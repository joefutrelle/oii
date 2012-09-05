from flask import Flask, request, url_for, abort, session, Response, render_template
from unittest import TestCase
import json
import re
import sys
import os
from time import strptime
from StringIO import StringIO
from oii.config import get_config
from oii.times import iso8601
from oii.webapi.utils import jsonr
import urllib
from oii.utils import order_keys
from oii.ifcb.formats.adc import read_adc, read_target, ADC, ADC_SCHEMA, TARGET_NUMBER, LEFT, BOTTOM, WIDTH, HEIGHT, STITCHED
from oii.ifcb.formats.roi import read_roi, read_rois, ROI
from oii.ifcb.formats.hdr import read_hdr, HDR, CONTEXT, HDR_SCHEMA
from oii.ifcb.db import IfcbFeed, IfcbFixity
from oii.resolver import parse_stream
from oii.ifcb.stitching import find_pairs, stitch, stitched_box, stitch_raw
from oii.io import UrlSource, LocalFileSource
from oii.image.pil.utils import filename2format, thumbnail
from oii.image import mosaic
from oii.image.mosaic import Tile
from oii.config import get_config
import mimetypes
from zipfile import ZipFile
from PIL import Image
from werkzeug.contrib.cache import SimpleCache

# TODO JSON on everything

app = Flask(__name__)
#app.debug = True

# importantly, set max-age on static files (e.g., javascript) to something really short
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30

# string key constants
STITCH='stitch'
NAMESPACE='namespace'
SIZE='size'
SCALE='scale'
PAGE='page'
PID='pid'
CACHE='cache'
CACHE_TTL='ttl'
PSQL_CONNECT='psql_connect'
FEED='feed'
FIXITY='fixity'
PORT='port'
DEBUG='debug'
STATIC='static'

# FIXME do this in main
# FIXME this should be selected by time series somehow
rs = parse_stream('oii/ifcb/mvco.xml')
binpid2path = rs['binpid2path']
pid_resolver = rs['pid']
blob_resolver = rs['mvco_blob']
lister = rs['list_adcs']

#for hit in lister.resolve_all():
#    print hit.value

def configure(config=None):
    app.config[CACHE] = SimpleCache()
    app.config[NAMESPACE] = 'http://demi.whoi.edu:5061/'
    app.config[STITCH] = True
    app.config[CACHE_TTL] = 120
    app.config[PSQL_CONNECT] = config.psql_connect
    app.config[FEED] = IfcbFeed(app.config[PSQL_CONNECT])
    app.config[FIXITY] = IfcbFixity(app.config[PSQL_CONNECT], rs)
    app.config[STATIC] = '/static/'
    try:
        if config.debug in ['True', 'true', 'T', 't', 'Yes', 'yes', 'debug']:
            app.debug = True
    except:
        pass
    try:
        app.config[PORT] = int(config.port)
    except:
        app.config[PORT] = 5061

def major_type(mimetype):
    return re.sub(r'/.*','',mimetype)

def minor_type(mimetype):
    return re.sub(r'.*/','',mimetype)

# simple memoization decorator using Werkzeug's caching support
def memoized(func):
    def wrap(*args):
        cache = app.config[CACHE] # get cache object from config
        # because the cache is shared across the entire app, we need
        # to include the function name in the cache key
        key = ' '.join([func.__name__] + map(str,args))
        result = cache.get(key)
        if result is None: # cache miss
            app.logger.debug('cache miss on %s' % str(key))
            result = func(*args) # produce the result
            # FIXME accept a TTL argument
            cache.set(key, result, timeout=app.config[CACHE_TTL]) # cache it
        return result
    return wrap

# utilities

def get_target(hit, adc_path=None):
    """Read a single target from an ADC file given the bin PID/LID and target number"""
    if adc_path is None:
        adc_path = resolve_adc(hit.bin_pid)
    for target in list_targets(hit, hit.target_no, adc_path=adc_path):
        return target

def image_response(image,format,mimetype):
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

def resolve_pid(pid):
    return pid_resolver.resolve(pid=pid)

def resolve_file(pid,format):
    return binpid2path.resolve(pid=pid,format=format).value

def resolve_adc(pid):
    return resolve_file(pid,ADC)

def resolve_hdr(pid):
    return resolve_file(pid,HDR)

def resolve_roi(pid):
    return resolve_file(pid,ROI)

def resolve_files(pid,formats):
    return [resolve_file(pid,format) for format in formats]

def parse_params(path, **defaults):
    """Parse a path fragment and convert to dict.
    Slashes separate alternating keys and values.
    For example /a/3/b/5 -> { 'a': '3', 'b': '5' }.
    Any keys not present get default values from **defaults"""
    parts = re.split('/',path)
    d = dict(zip(parts[:-1:2], parts[1::2]))
    for k,v in defaults.items():
        if k not in d:
            d[k] = v
    return d

def parse_date_param(sdate):
    try:
        return strptime(sdate,'%Y-%m-%d')
    except:
        pass
    try:
        return strptime(sdate,'%Y-%m-%dT%H:%M:%S')
    except:
        pass
    try:
        return strptime(sdate,'%Y-%m-%dT%H:%M:%SZ')
    except:
        pass
    try:
        return strptime(re.sub(r'\.\d+Z','',sdate),'%Y-%m-%dT%H:%M:%S')
    except:
        app.logger.debug('could not parse date param %s' % sdate)


def binlid2dict(time_series, bin_lid):
    hit = pid_resolver.resolve(pid=bin_lid, time_series=time_series)
    date = iso8601(strptime(hit.date, hit.date_format))
    return {
        'lid': bin_lid,
        'pid': hit.bin_pid,
        'date': date
        }

@app.route('/<time_series>/api/feed/format/<format>')
@app.route('/<time_series>/api/feed/date/<date>/format/<format>')
def serve_feed(time_series,date=None,format='json'):
    if date is not None:
        date = parse_date_param(date)
    # FIXME support formats other than JSON, also use extension
    def feed2dicts():
        # FIXME choose feed based on time series!
        for bin_lid in app.config[FEED].latest_bins(date):
            yield binlid2dict(time_series, bin_lid)
    return jsonr(list(feed2dicts()))

@app.route('/<time_series>/api/feed/nearest/<date>')
def serve_nearest(time_series,date):
    if date is not None:
        date = parse_date_param(date)
    # FIXME choose feed based on time series!
    for bin_lid in app.config[FEED].nearest_bin(date):
        d = binlid2dict(time_series, bin_lid)
    return jsonr(d)

@memoized
def get_volume():
    return json.dumps(app.config[FIXITY].summarize_data_volume())

@app.route('/api/volume')
def serve_volume():
    return Response(get_volume(), mimetype='application/json')

@app.route('/api/mosaic/pid/<path:pid>')
def serve_mosaic(pid):
    """Serve a mosaic with all-default parameters"""
    hit = pid_resolver.resolve(pid=pid)
    if hit.extension == 'html': # here we generate an HTML representation with multiple pages
        return Response(render_template('mosaics.html',hit=hit),mimetype='text/html')
    else:
        return serve_mosaic(pid) # default mosaic image

@memoized
def get_sorted_tiles(bin_pid): # FIXME support multiple sort options
    adc_path = resolve_adc(bin_pid)
    hit = resolve_pid(bin_pid)
    # read ADC and convert to Tiles in size-descending order
    def descending_size(t):
        (w,h) = t.size
        return 0 - (w * h)
    # using read_target means we don't stitch. this is simply for performance.
    tiles = [Tile(t, (t[HEIGHT], t[WIDTH])) for t in list_targets(hit, adc_path=adc_path)]
    # FIXME instead of sorting tiles, sort targets to allow for non-geometric sort options
    tiles.sort(key=descending_size)
    return tiles

@memoized
def get_mosaic_layout(pid, scaled_size, page):
    tiles = get_sorted_tiles(pid)
    # perform layout operation
    return mosaic.layout(tiles, scaled_size, page, threshold=0.05)

def layout2json(layout, scale):
    """Doesn't actually produce JSON but rather JSON-serializable representation of the tiles"""
    for t in layout:
        (w,h) = t.size
        (x,y) = t.position
        yield dict(pid=t.image['pid'], width=w*scale, height=h*scale, x=x*scale, y=y*scale)

@app.route('/api/mosaic/<path:params>/pid/<path:pid>')
def serve_mosaic(pid, params='/'):
    """Generate a mosaic of ROIs from a sample bin.
    params include the following, with default values
    - series (mvco) - time series (FIXME: handle with resolver, clarify difference between namespace, time series, pid, lid)
    - size (1024x1024) - size of the mosaic image
    - page (1) - page. for typical image sizes the entire bin does not fit and so is split into pages.
    - scale - scaling factor for image dimensions """
    # parse params
    params = parse_params(params, size='1024x1024',page=1,scale=1.0)
    (w,h) = tuple(map(int,re.split('x',params[SIZE])))
    scale = float(params[SCALE])
    page = int(params[PAGE])
    # parse pid/lid
    hit = pid_resolver.resolve(pid=pid)
    # perform layout operation
    scaled_size = (int(w/scale), int(h/scale))
    layout = get_mosaic_layout(hit.bin_pid, scaled_size, page)
    # serve JSON on request
    if hit.extension == 'json':
        return jsonr(list(layout2json(layout, scale)))
    # resolve ROI file
    roi_path = resolve_roi(hit.bin_pid)
    # read all images needed for compositing and inject into Tiles
    with open(roi_path,'rb') as roi_file:
        for tile in layout:
            target = tile.image
            # FIXME use fast stitching
            tile.image = get_roi_image(hit.bin_pid, target[TARGET_NUMBER], fast_stitching=True)
    # produce and serve composite image
    mosaic_image = thumbnail(mosaic.composite(layout, scaled_size, mode='L', bgcolor=160), (w,h))
    (pil_format, mimetype) = image_types(hit)
    return image_response(mosaic_image, pil_format, mimetype)
    
@app.route('/api/blob/pid/<path:pid>')
def serve_blob(pid):
    """Serve blob zip or image"""
    hit = blob_resolver.resolve(pid=pid)
    zip_path = hit.value
    if hit.target is None: # bin, not target?
        if hit.extension != 'zip':
            abort(404)
        # the zip file is on disk, stream it directly to client
        return Response(file(zip_path), direct_passthrough=True, mimetype='application/zip')
    else: # target, not bin
        blobzip = ZipFile(zip_path)
        png = blobzip.read(hit.lid+'.png')
        blobzip.close()
        # now determine PIL format and MIME type
        (pil_format, mimetype) = image_types(hit)
        if mimetype == 'image/png':
            return Response(png, mimetype='image/png')
        else:
            # FIXME support more imaage types
            blob_image = Image.open(StringIO(png))
            return image_response(blob_image, pil_format, mimetype)

@app.route('/<time_series>/api/<path:ignore>')
def api_error(time_series,ignore):
    abort(404)

@app.route('/<path:pid>')
def resolve(pid):
    """Resolve a URL to some data endpoint in a time series, including bin and target metadata endpoints,
    and image endpoints"""
    # use the PID resolver (which also works for LIDs)
    #app.logger.debug('attempting to resolve '+pid)
    hit = resolve_pid(pid)
    if hit is None:
        abort(404)
    # construct the namespace from the configuration and time series ID
    #hit.namespace = '%s%s/' % (app.config[NAMESPACE], time_series)
    #hit.bin_pid = hit.namespace + hit.bin_lid
    hit.date = iso8601(strptime(hit.date, hit.date_format))
    # determine extension
    if hit.extension is None: # default is .rdf
        hit.extension = 'rdf'
    # determine MIME type
    filename = '%s.%s' % (hit.lid, hit.extension)
    (mimetype, _) = mimetypes.guess_type(filename)
    if mimetype is None:
        mimetype = 'application/octet-stream'
    # is this request for a product?
    if hit.product == 'blob':
        return serve_blob(hit.pid)
    # is the request for a single target?
    if hit.target is not None:
        hit.target_no = int(hit.target) # parse target number
        if major_type(mimetype) == 'image': # need an image?
            return serve_roi(hit) # serve it
        else:  # otherwise serve metadata
            hit.target_pid = hit.namespace + hit.lid # construct target pid
            return serve_target(hit,mimetype)
    else: # nope, it's for a whole bin
        return serve_bin(hit,mimetype)
    # nothing recognized, so return Not Found
    abort(404)

@app.route('/<time_series>/dashboard')
@app.route('/<time_series>/dashboard/<path:pid>')
def serve_timeseries(time_series, pid=None):
    template = dict(static=app.config[STATIC])
    if pid is not None:
        hit = pid_resolver.resolve(pid=pid)
        template['pid'] = hit.bin_pid
        template['time_series'] = hit.time_series
    else:
        template['time_series'] = time_series
    return Response(render_template('timeseries.html',**template), mimetype='text/html')

@memoized
def read_targets(adc_path, target_no=1, limit=-1):
    return list(read_adc(LocalFileSource(adc_path), target_no, limit))

def list_targets(hit, target_no=1, limit=-1, adc_path=None, stitch_targets=None):
    if stitch_targets is None:
        stitch_targets = app.config[STITCH]
    if adc_path is None:
        adc_path = resolve_adc(hit.bin_pid)
    targets = read_targets(adc_path, target_no, limit)
    if stitch_targets:
        # in the stitching case we need to compute "stitched" flags based on pairs
        # correct image metrics
        Bs = []
        for a,b in find_pairs(targets):
            (a[LEFT], a[BOTTOM], a[WIDTH], a[HEIGHT]) = stitched_box([a,b])
            a[STITCHED] = 1
            b[STITCHED] = 0
            Bs.append(b)
        # exclude the second of each pair from the list of targets
        app.logger.debug('number of targets (pre-stitched): %d, number of pairs: %d' % (len(targets),len(Bs)))
        targets = filter(lambda target: target not in Bs, targets)
        app.logger.debug('number of targets (post-stitched): %d' % len(targets))
    for target in targets:
        if not STITCHED in target:
            target[STITCHED] = 0
        # add a binID and pid what are the right keys for these?
        target['binID'] = '%s' % hit.bin_pid
        target['pid'] = '%s_%05d' % (hit.bin_pid, target[TARGET_NUMBER])
    return targets

def csv_quote(thing):
    if re.match(r'^-?[0-9]+(\.[0-9]+)?$',thing):
        return thing
    else:
        return '"' + thing + '"'

def bin2csv(hit,targets):
    # get the ADC keys for this version of the ADC format
    schema_keys = [k for k,_ in ADC_SCHEMA[hit.schema_version]]
    def csv_iter():
        first = True
        for target in targets:
            # now order all keys even the ones not in the schema
            keys = order_keys(target, schema_keys)
            # fetch all the data for this row as strings
            row = [str(target[k]) for k in keys]
            if first: # if this is the first row, emit the keys
                yield ','.join(keys)
                first = False
            # now emit the row
            yield ','.join(map(csv_quote,row))
    return Response(render_template('bin.csv',rows=csv_iter()),mimetype='text/plain')

def serve_bin(hit,mimetype):
    """Serve a sample bin in some format"""
    # for raw files, simply pass the file through
    if hit.extension == ADC:
        return Response(file(resolve_adc(hit.bin_pid)), direct_passthrough=True, mimetype='text/csv')
    elif hit.extension == ROI:
        return Response(file(resolve_roi(hit.bin_pid)), direct_passthrough=True, mimetype='application/octet-stream')
    # at this point we need to resolve the HDR file
    hdr_path = resolve_hdr(hit.bin_pid)
    if hit.extension == HDR:
        return Response(file(hdr_path), direct_passthrough=True, mimetype='text/plain')
    props = read_hdr(LocalFileSource(hdr_path))
    context = props[CONTEXT]
    del props[CONTEXT]
    # sort properties according to their order in the header schema
    props = [(k,props[k]) for k,_ in HDR_SCHEMA]
    # get a list of all targets, taking into account stitching
    targets = list_targets(hit)
    target_pids = ['%s_%05d' % (hit.bin_pid, target['targetNumber']) for target in targets]
    template = dict(hit=hit,context=context,properties=props,targets=targets,target_pids=target_pids,static=app.config[STATIC])
    if minor_type(mimetype) == 'xml':
        return Response(render_template('bin.xml',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'rdf+xml':
        return Response(render_template('bin.rdf',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'csv':
        return bin2csv(hit,targets)
    elif mimetype == 'text/html':
        return Response(render_template('bin.html',**template), mimetype='text/html')
    elif mimetype == 'application/json':
        properties = dict(props)
        properties['context'] = context
        properties['targets'] = targets
        return jsonr(properties)
    else:
        abort(404)

def serve_target(hit,mimetype):
    target = get_target(hit) # read the target from the ADC file
    properties = target
    # sort the target properties according to the order in the schema
    schema_keys = [k for k,_ in ADC_SCHEMA[hit.schema_version]]
    target = [(k,target[k]) for k in order_keys(target, schema_keys)]
    # now populate the template appropriate for the MIME type
    template = dict(hit=hit,target=target,properties=properties,static=app.config[STATIC])
    if minor_type(mimetype) == 'xml':
        return Response(render_template('target.xml',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'rdf+xml':
        return Response(render_template('target.rdf',**template), mimetype='text/xml')
    elif mimetype == 'text/html':
        return Response(render_template('target.html',**template), mimetype='text/html')
    elif mimetype == 'application/json':
        return jsonr(dict(target))
    print minor_type(mimetype)

def image_types(hit):
    # now determine PIL format and MIME type
    filename = '%s.%s' % (hit.lid, hit.extension)
    pil_format = filename2format(filename)
    (mimetype, _) = mimetypes.guess_type(filename)
    return (pil_format, mimetype)

def get_roi_image(bin_pid, target_no, fast_stitching=False):
    """Serve a stitched ROI image given the output of the pid resolver"""
    # resolve the ADC and ROI files
    (adc_path, roi_path) = resolve_files(bin_pid, (ADC, ROI))
    if app.config[STITCH]:
        offset=max(1,target_no-1)
        limit=3 # read three targets, in case we need to stitch
    else:
        offset=target_no
        limit=1 # just read one
    targets = list(read_targets(adc_path, offset, limit))
    if len(targets) == 0: # no targets? return Not Found
        return None
    # open the ROI file as we may need to read more than one
    with open(roi_path,'rb') as roi_file:
        if app.config[STITCH]:
            pairs = list(find_pairs(targets)) # look for stitched pairs
        else:
            pairs = targets
        roi_image = None
        if len(pairs) >= 1: # found one?
            (a,b) = pairs[0] # split pair
            if b[TARGET_NUMBER] == target_no: # second of a pair?
                return None
            images = list(read_rois((a,b),roi_file=roi_file)) # read the images
            if fast_stitching:
                roi_image = stitch_raw((a,b), images, background=180)
            else:
                (roi_image, mask) = stitch((a,b), images) # stitch them
        else:
            # now check that the target number is correct
            for target in targets:
                if target[TARGET_NUMBER] == target_no:
                    images = list(read_rois([target],roi_file=roi_file)) # read the image
                    roi_image = images[0]
        return roi_image

def serve_roi(hit):
    """Serve a stitched ROI image given the output of the pid resolver"""
    roi_image = get_roi_image(hit.bin_pid, hit.target_no)
    if roi_image is None:
        abort(404)
    # now determine PIL format and MIME type
    (pil_format, mimetype) = image_types(hit)
    # return the image data
    return image_response(roi_image,pil_format,mimetype)

if __name__=='__main__':
    """First argument is a config file which must at least have psql_connect in it
    to support feed arguments. Filesystem config is in the resolver."""
    if len(sys.argv) > 1:
        configure(get_config(sys.argv[1]))
    else:
        configure()
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0',port=app.config[PORT])
