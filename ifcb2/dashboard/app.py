import os
import mimetypes
import json
from time import strptime
from io import BytesIO
import re
import PIL
from array import array
from zipfile import ZipFile
from lxml import html
from StringIO import StringIO

from flask import Flask, Response, abort, request, render_template, render_template_string, redirect
import flask.ext.sqlalchemy
import flask.ext.restless

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import numpy as np

from skimage.segmentation import find_boundaries

from oii.utils import coalesce, memoize
from oii.times import iso8601, parse_date_param, struct_time2utcdatetime
from oii.image.io import as_bytes, as_pil
from oii.image import mosaic
from oii.image.mosaic import Tile

# FIXME this is used for old PIL-based mosaic compositing API
from oii.image.pil.utils import filename2format, thumbnail

from oii.ifcb2 import get_resolver
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User

from oii.ifcb2.feed import Feed
from oii.ifcb2.formats.adc import Adc

from oii.ifcb2.files import parsed_pid2fileset, NotFound
from oii.ifcb2.identifiers import add_pids, add_pid, canonicalize
from oii.ifcb2.represent import split_hdr, targets2csv, bin2xml, bin2json, bin2rdf, bin2zip, target2xml, target2rdf, bin2json_short, bin2json_medium
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.hdr import parse_hdr_file
from oii.ifcb2.accession import fast_accession
# keys
from oii.ifcb2.identifiers import PID, LID, ADC_COLS, SCHEMA_VERSION, TIMESTAMP, TIMESTAMP_FORMAT, PRODUCT
from oii.ifcb2.formats.adc import HEIGHT, WIDTH, TARGET_NUMBER
from oii.ifcb2.stitching import STITCHED

# constants

MIME_JSON='application/json'

# eventually the session cofiguration should
# go in its own class.
#SQLITE_URL='sqlite:///home/ubuntu/dev/ifcb_admin.db'
SQLITE_URL='sqlite:///ifcb_admin.db'

from sqlalchemy.pool import StaticPool
dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

STATIC='/static/'
app = Flask(__name__)

### generic flask utils ###
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

def max_age(ttl=None):
    if ttl is None:
        return {}
    else:
        return {'Cache-control': 'max-age=%d' % ttl}

def template_response(template, mimetype=None, ttl=None, **kw):
    if mimetype is None:
        (mimetype, _) = mimetypes.guess_type(template)
    if mimetype is None:
        mimetype = 'application/octet-stream'
    return Response(render_template(template,**kw), mimetype=mimetype, headers=max_age(ttl))

#### generic IFCB utils #####
# FIXME refactor!

def ifcb():
    return get_resolver().ifcb

@memoize(ttl=30)
def parse_pid(pid):
    try:
        return next(ifcb().pid(pid))
    except StopIteration:
        raise

@memoize(ttl=30)
def get_data_roots(ts_label, product_type='raw'):
    dds = session.query(DataDirectory)\
                .join(TimeSeries)\
                .filter(TimeSeries.label==ts_label)\
                .filter(DataDirectory.product_type==product_type)
    paths = []
    for data_dir in dds:
        paths.append(data_dir.path)
    return paths

def get_timestamp(parsed_pid):
    return iso8601(strptime(parsed_pid[TIMESTAMP], parsed_pid[TIMESTAMP_FORMAT]))

def get_targets(adc, bin_pid):
    # unstitched for now
    us_targets = add_pids(adc.get_targets(),bin_pid)
    for us_target in us_targets:
        # claim all are unstitched
        us_target[STITCHED] = False
        yield us_target

@memoize(ttl=30,key=lambda args: frozenset(args[0].items()))
def get_fileset(parsed):
    time_series = parsed['ts_label']
    data_roots = list(get_data_roots(time_series))
    schema_version = parsed[SCHEMA_VERSION]
    adc_cols = parsed[ADC_COLS].split(' ')
    return parsed_pid2fileset(parsed,data_roots)

@memoize(ttl=30,key=lambda args: frozenset(args[0].items() + [args[1]]))
def get_product_file(parsed, product_type):
    parsed = dict(parsed.items())
    time_series = parsed['ts_label']
    data_roots = list(get_data_roots(time_series,product_type))
    parsed['product'] = product_type
    for root in data_roots:
        try:
            hit = next(get_resolver().ifcb.files.find_product(root=root,**parsed))
            return hit['product_path']
        except StopIteration:
            pass
    raise NotFound

def serve_blob_bin(parsed):
    blob_zip = get_product_file(parsed, 'blobs')
    return Response(file(blob_zip), direct_passthrough=True, mimetype='application/zip')

def serve_features_bin(parsed):
    feature_csv = get_product_file(parsed, 'features')
    return Response(file(feature_csv), direct_passthrough=True, mimetype='text/csv')

def serve_blob_image(parsed, mimetype, outline=False, target_img=None):
    # first, read the blob from the zipfile
    blob_zip = get_product_file(parsed, 'blobs')
    zipfile = ZipFile(blob_zip)
    png_name = parsed['lid'] + '.png' # name is target LID + png extension
    png_data = zipfile.read(png_name)
    zipfile.close()
    # if we want a blob png, then pass it through without conversion
    if not outline and mimetype == 'image/png':
        return Response(png_data, mimetype='image/png')
    else:
        # read the png-formatted blob image into a PIL image
        pil_img = PIL.Image.open(StringIO(png_data))
        blob = np.array(pil_img.convert('L')) # convert to 8-bit grayscale
        if not outline: # unless we are drawing the outline
            return Response(as_bytes(blob), mimetype=mimetype) # format and serve
        else:
            blob_outline = find_boundaries(blob)
            roi = target_img
            blob = np.dstack([roi,roi,roi])
            blob[blob_outline] = [255,0,0]
            return Response(as_bytes(blob, mimetype), mimetype=mimetype)

############# ENDPOINTS ##################

@app.route('/api')
@app.route('/api.html')
def serve_doc():
    template = dict(static=STATIC)
    return template_response('api.html', **template)

@app.route('/about')
@app.route('/about.html')
def serve_about():
    template = dict(static=STATIC)
    return template_response('help.html', **template)

### timeseries endpoints ###

@app.route('/')
@app.route('/<ts_label>')
@app.route('/<ts_label>/')
@app.route('/<ts_label>/dashboard')
@app.route('/<ts_label>/dashboard/')
@app.route('/<ts_label>/dashboard/<path:pid>')
def serve_timeseries(ts_label=None, pid=None):
    template = dict(static=STATIC, time_series=ts_label)
    if pid is not None:
        template['pid'] = pid
    # fetch time series information
    all_series = []
    for ts in session.query(TimeSeries).filter(TimeSeries.enabled):
        if ts_label is None: # no time series specified
            return redirect(os.path.join(request.url_root, ts.label), code=302)
        if ts.label == ts_label:
            template['page_title'] = html.fromstring(ts.description).text_content()
            template['title'] = ts.description
        all_series.append((ts.label, ts.description))
    template['all_series'] = all_series
    template['base_url'] = request.url_root
    return template_response('timeseries.html', **template)

### data volume by day ###
@app.route('/<ts_label>/api/volume')
def volume(ts_label):
    dv = []
    with Feed(session, ts_label) as feed:
        for row in feed.daily_data_volume():
            dv.append({
                'gb': float(row[0]),
                'bin_count': row[1],
                'day': row[2]
            })
    return Response(json.dumps(dv), mimetype=MIME_JSON)

### feed API ###

@app.route('/<ts_label>/api/feed/nearest/<timestamp>')
def nearest(ts_label, timestamp):
    ts = struct_time2utcdatetime(parse_date_param(timestamp))
    with Feed(session, ts_label) as feed:
        for bin in feed.nearest(timestamp=ts):
            break
    sample_time_str = iso8601(bin.sample_time.timetuple())
    pid = canonicalize(request.url_root, ts_label, bin.lid)
    resp = dict(pid=pid, date=sample_time_str)
    return Response(json.dumps(resp), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/feed/<after_before>/pid/<path:pid>')
@app.route('/<ts_label>/api/feed/<after_before>/n/<int:n>/pid/<path:pid>')
def serve_after_before(ts_label,after_before,n=1,pid=None):
    if not after_before in ['before','after']:
        abort(400)
    try:
        parsed = next(ifcb().pid(pid))
    except StopIteration:
        abort(404)
    bin_lid = parsed['bin_lid']
    with Feed(session, ts_label) as feed:
        if after_before=='before':
            bins = list(feed.before(bin_lid, n))
        else:
            bins = list(feed.after(bin_lid, n))
    resp = []
    for bin in bins:
        sample_time_str = iso8601(bin.sample_time.timetuple())
        pid = canonicalize(request.url_root, ts_label, bin.lid)
        resp.append(dict(pid=pid, date=sample_time_str))
    return Response(json.dumps(resp), mimetype='application/json')

### data validation and accession ###

@app.route('/api/accession')
@app.route('/api/accession/<ts_label>')
def accession(ts_label=None):
    results = []
    tss = []
    if ts_label is None:
        for ts in session.query(TimeSeries).filter(TimeSeries.enabled):
            results.append(ts)
    else:
        tss = [session.query(TimeSeries).first()]
    for ts in tss:
        for ddir in ts.data_dirs:
            if ddir.product_type != 'raw':
                continue
            try:
                (n_new, n_total) = fast_accession(session, ts.label, ddir.path)
                results.append({
                    'time_series': ts.label,
                    'data_dir': ddir.path,
                    'status': 'found',
                    'new': n_new,
                    'total': n_total
                })
            except:
                results.append({
                    'time_series': ts.label,
                    'data_dir': ddir.path,
                    'status': 'not found'
                });
    return Response(json.dumps(results), mimetype='application/json')

### bins, targets, and products ###

@app.route('/<path:pid>')
def hello_world(pid):
    try:
        parsed = parse_pid(pid)
    except StopIteration:
        abort(404)
    time_series = parsed['ts_label']
    bin_lid = parsed['bin_lid']
    lid = parsed[LID]
    url_root = request.url_root
    canonical_pid = canonicalize(url_root, time_series, lid)
    schema_version = parsed[SCHEMA_VERSION]
    try:
        paths = get_fileset(parsed)
    except NotFound:
        abort(404)
    hdr_path = paths['hdr_path']
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    adc = Adc(adc_path, schema_version)
    extension = 'json' # default
    product = parsed[PRODUCT]
    heft = 'full' # heft is either short, medium, or full
    if 'extension' in parsed:
        extension = parsed['extension']
    timestamp = get_timestamp(parsed)
    if 'target' in parsed:
        canonical_bin_pid = canonicalize(url_root, time_series, bin_lid)
        target_no = parsed['target']
        target = adc.get_target(target_no)
        add_pid(target, canonical_bin_pid)
        if extension == 'json':
            return Response(json.dumps(target),mimetype=MIME_JSON)
        # not JSON, check for image
        mimetype = mimetypes.types_map['.' + extension]
        if mimetype.startswith('image/'):
            if product=='raw':
                img = read_target_image(target, roi_path)
                return Response(as_bytes(img,mimetype),mimetype=mimetype)
            if product=='blob':
                return serve_blob_image(parsed, mimetype)
            if product=='blob_outline':
                img = read_target_image(target, roi_path)
                return serve_blob_image(parsed, mimetype, outline=True, target_img=img)
        # more metadata representations. we'll need the header
        hdr = parse_hdr_file(hdr_path)
        if extension == 'xml':
            return Response(target2xml(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension == 'rdf':
            return Response(target2rdf(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension in ['html', 'htm']:
            template = {
                'static': STATIC,
                'target_pid': canonical_pid,
                'bin_pid': canonical_bin_pid,
                'properties': target,
                'target': target.items(), # FIXME use order_keys
                'date': timestamp
            }
            return template_response('target.html',**template)
    else: # bin
        if extension in ['hdr', 'adc', 'roi']:
            path = dict(hdr=hdr_path, adc=adc_path, roi=roi_path)[extension]
            mimetype = dict(hdr='text/plain', adc='text/csv', roi='application/octet-stream')[extension]
            return Response(file(path), direct_passthrough=True, mimetype=mimetype)
        if product=='blob':
            return serve_blob_bin(parsed)
        if product=='features':
            return serve_features_bin(parsed)
        # gonna need targets unless heft is medium or below
        targets = []
        if product != 'short':
            targets = get_targets(adc, canonical_pid)
        if extension=='csv':
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines)+'\n',mimetype='text/csv')
        # we'll need the header for the other representations
        hdr = parse_hdr_file(hdr_path)
        # and the timestamp
        timestamp = iso8601(strptime(parsed['timestamp'], parsed['timestamp_format']))
        if extension in ['html', 'htm']:
            targets = list(targets)
            context, props = split_hdr(hdr)
            template = {
                'static': STATIC,
                'bin_pid': canonical_pid,
                'time_series': time_series,
                'context': context,
                'properties': props,
                'targets': targets,
                'target_pids': [t['pid'] for t in targets],
                'date': timestamp
            }
            return template_response('bin.html', **template)
        if extension=='json':
            if product=='short':
                return Response(bin2json_short(canonical_pid,hdr,timestamp),mimetype=MIME_JSON)
            if product=='medium':
                return Response(bin2json_medium(canonical_pid,hdr,targets,timestamp),mimetype=MIME_JSON)
            return Response(bin2json(canonical_pid,hdr,targets,timestamp),mimetype=MIME_JSON)
        if extension=='xml':
            return Response(bin2xml(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='rdf':
            return Response(bin2rdf(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='zip':
            buffer = BytesIO()
            bin2zip(parsed,canonical_pid,targets,hdr,timestamp,roi_path,buffer)
            return Response(buffer.getvalue(), mimetype='application/zip')
    return 'unimplemented'

#### mosaics #####

@memoize
def get_sorted_tiles(adc_path, schema_version, bin_pid):
    # read ADC and convert to Tiles in size-descending order
    def descending_size(t):
        (w,h) = t.size
        return 0 - (w * h)
    adc = Adc(adc_path, schema_version)
    # using read_target means we don't stitch. this is simply for performance.
    tiles = [Tile(t, (t[HEIGHT], t[WIDTH])) for t in get_targets(adc, bin_pid)]
    # FIXME instead of sorting tiles, sort targets to allow for non-geometric sort options
    tiles.sort(key=descending_size)
    return tiles

@memoize
def get_mosaic_layout(adc_path, schema_version, bin_pid, scaled_size, page):
    tiles = get_sorted_tiles(adc_path, schema_version, bin_pid)
    # perform layout operation
    return list(mosaic.layout(tiles, scaled_size, page, threshold=0.05))

def layout2json(layout, scale):
    """Doesn't actually produce JSON but rather JSON-serializable representation of the tiles"""
    for t in layout:
        (w,h) = t.size
        (x,y) = t.position
        yield dict(pid=t.image['pid'], width=int(w*scale), height=int(h*scale), x=int(x*scale), y=int(y*scale))

@app.route('/<time_series>/api/mosaic/<path:params>/pid/<path:pid>')
def serve_mosaic_image(time_series=None, pid=None, params='/'):
    """Generate a mosaic of ROIs from a sample bin.
    params include the following, with default values
    - series (mvco) - time series (FIXME: handle with resolver, clarify difference between namespace, time series, pid, lid)
    - size (1024x1024) - size of the mosaic image
    - page (1) - page. for typical image sizes the entire bin does not fit and so is split into pages.
    - scale - scaling factor for image dimensions """
    # parse params
    SIZE, SCALE, PAGE = 'size', 'scale', 'page'
    params = parse_params(params, size='1024x1024',page=1,scale=1.0)
    (w,h) = tuple(map(int,re.split('x',params[SIZE])))
    scale = float(params[SCALE])
    page = int(params[PAGE])
    # parse pid/lid
    parsed = parse_pid(pid)
    schema_version = parsed['schema_version']
    try:
        paths = get_fileset(parsed)
    except NotFound:
        abort(404)
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    bin_pid = canonicalize(request.url_root, time_series, parsed['bin_lid'])
    # perform layout operation
    scaled_size = (int(w/scale), int(h/scale))
    layout = list(get_mosaic_layout(adc_path, schema_version, bin_pid, scaled_size, page))
    extension = parsed['extension']
    # serve JSON on request
    if extension == 'json':
        return Response(json.dumps(list(layout2json(layout, scale))), mimetype=MIME_JSON)
    mimetype = mimetypes.types_map['.' + extension]
    # read all images needed for compositing and inject into Tiles
    image_layout = []
    with open(roi_path,'rb') as roi_file:
        for tile in layout:
            target = tile.image # in mosaic API, the record is called 'image'
            # FIXME 1. replace PIL 2. use fast stitching
            image = PIL.Image.fromarray(read_target_image(target, roi_path))
            image_layout.append(Tile(image, tile.size, tile.position))
    # produce and serve composite image
    mosaic_image = thumbnail(mosaic.composite(image_layout, scaled_size, mode='L', bgcolor=160), (w,h))
    #pil_format = filename2format('foo.%s' % extension)
    return Response(as_bytes(mosaic_image), mimetype=mimetype)

### admin API hacked right on in ####

API_URL_PREFIX = '/admin/api/v1'

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    if data.has_key('edit'):
        print "*************************************************"
        print data
        print "*************************************************"
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        data.pop('edit')

manager = flask.ext.restless.APIManager(app, session=session)
manager.create_api(
    TimeSeries,
    url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE': [patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    DataDirectory,
    url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    User,
    url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )

if __name__ == '__main__':
    Base.metadata.create_all(dbengine)
    app.run(host='0.0.0.0',port=8080,debug=True)
