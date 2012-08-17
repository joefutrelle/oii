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
from oii.ifcb.formats.adc import read_adc, read_target, ADC_SCHEMA, TARGET_NUMBER, WIDTH, HEIGHT, STITCHED
from oii.ifcb.formats.roi import read_roi, read_rois
from oii.ifcb.formats.hdr import read_hdr, CONTEXT, HDR_SCHEMA
from oii.resolver import parse_stream
from oii.ifcb.stitching import find_pairs, stitch
from oii.io import UrlSource, LocalFileSource
from oii.image.pil.utils import filename2format
from oii.image import mosaic
from oii.image.mosaic import Tile
import mimetypes

app = Flask(__name__)
app.debug = True

# importantly, set max-age on static files (e.g., javascript) to something really short
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30
rs = parse_stream('oii/ifcb/mvco.xml')
binpid2path = rs['binpid2path']
pid_resolver = rs['pid']

# config options
STITCH='stitch'
NAMESPACE='namespace'

def configure(config):
    # FIXME populate app.config dict
    pass

app.config[NAMESPACE] = 'http://demi.whoi.edu:5061/'
app.config[STITCH] = True

def major_type(mimetype):
    return re.sub(r'/.*','',mimetype)

def minor_type(mimetype):
    return re.sub(r'.*/','',mimetype)

# utilities

def get_target(bin,target_no):
    """Read a single target from an ADC file given the bin PID/LID and target number"""
    adc_path = binpid2path.resolve(pid=bin,format='adc').value
    if not app.config[STITCH]: # no stitching, read one target
        return read_target(LocalFileSource(adc_path), target_no)
    else:
        # in the stitching case we need to read two targets and see if they overlap,
        # so we can set the STITCHED flag
        targets = list(read_adc(LocalFileSource(adc_path), target_no, limit=2))
        target = targets[0]
        if len(list(find_pairs(targets))) > 1:
            target[STITCHED] = 1
        else:
            target[STITCHED] = 0
        return target

def image_response(image,format,mimetype):
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/api/foo/<bar>')
def foo(bar):
    d = dict(a='foo', b=bar)
    return Response(render_template('foo.xml',d=d), mimetype='text/xml')

@app.route('/<time_series>/api/mosaic/pid/<path:pid>')
@app.route('/<time_series>/api/mosaic/size/<size>/pid/<path:pid>')
@app.route('/<time_series>/api/mosaic/page/<int:page>/pid/<path:pid>')
@app.route('/<time_series>/api/mosaic/size/<size>/page/<int:page>/pid/<path:pid>')
def serve_mosaic(time_series,size='1024x1024',page=1,pid=None):
    hit = pid_resolver.resolve(pid=pid)
    (pil_format, mimetype) = image_types(hit)
    adc_path = binpid2path.resolve(pid=hit.bin_lid,format='adc').value
    size = tuple(map(int,re.split('x',size)))
    def descending_size(t):
        (w,h) = t.size
        return 0 - (w * h)
    tiles = sorted([Tile(t, (t[HEIGHT], t[WIDTH])) for t in read_adc(LocalFileSource(adc_path))], key=descending_size)
    layout = list(mosaic.layout(tiles, size))
    roi_path = binpid2path.resolve(pid=hit.bin_lid,format='roi').value
    with open(roi_path,'rb') as roi_file:
        for tile in layout:
            target = tile.image
            for roi in read_rois([target], roi_file=roi_file):
                tile.image = roi # should only iterate once
    # for now serve images, but should serve tiles too
    mosaic_image = mosaic.composite(layout, size, mode='L', bgcolor=160)
    return image_response(mosaic_image, pil_format, mimetype)

@app.route('/<time_series>/api/<path:ignore>')
def api_error(time_series,ignore):
    abort(404)

@app.route('/<time_series>/<path:lid>')
def resolve(time_series,lid):
    """Resolve a URL to some data endpoint in a time series, including bin and target metadata endpoints,
    and image endpoints"""
    # use the PID resolver (which also works for LIDs)
    hit = pid_resolver.resolve(pid=lid)
    # construct the namespace from the configuration and time series ID
    hit.namespace = '%s%s/' % (app.config[NAMESPACE], time_series)
    hit.bin_pid = hit.namespace + hit.bin_lid
    hit.date = iso8601(strptime(hit.date, hit.date_format))
    # determine extension
    if hit.extension is None: # default is .rdf
        hit.extension = 'rdf'
    # determine MIME type
    filename = '%s.%s' % (hit.lid, hit.extension)
    (mimetype, _) = mimetypes.guess_type(filename)
    # is the user requesting an image?
    if hit.target is not None:
        hit.target_no = int(hit.target) # parse target number
    if major_type(mimetype) == 'image':
        return serve_roi(hit)
    else:
        if hit.target is not None: # is this a target endpoint (rather than a bin endpoint?)
            hit.target_pid = hit.namespace + hit.lid # construct target pid
            return serve_target(hit,mimetype)
        else:
            return serve_bin(hit,mimetype)
    # nothing recognized, so return Not Found
    abort(404)

def list_targets(hit):
    adc_path = binpid2path.resolve(pid=hit.bin_lid,format='adc').value
    targets = list(read_adc(LocalFileSource(adc_path)))
    if app.config[STITCH]:
        # in the stitching case we need to compute "stitched" flags based on pairs
        pairs = find_pairs(targets)
        As = [a for (a,_) in pairs]
        for target in targets:
            if target in As:
                target[STITCHED] = 1
            else:
                target[STITCHED] = 0
        # and we have to exclude the second of each pair from the list of targets
        Bs = [b for (_,b) in pairs]
        targets = filter(lambda target: target not in Bs, targets)
    return targets
    
def bin2csv(hit,targets):
    # get the ADC keys for this version of the ADC format
    schema_keys = [k for k,_ in ADC_SCHEMA[hit.schema_version]]
    def csv_iter():
        first = True
        for target in targets:
            # add a binID and pid what are the right keys for these?
            target['binID'] = '"%s"' % hit.bin_pid
            target['pid'] = '"%s_%05d"' % (hit.bin_pid, target['targetNumber'])
            # now order all keys even the ones not in the schema
            keys = order_keys(target, schema_keys)
            # fetch all the data for this row as strings
            row = [str(target[k]) for k in keys]
            if first: # if this is the first row, emit the keys
                yield ','.join(keys)
                first = False
            # now emit the row
            yield ','.join(row)
    return Response(render_template('bin.csv',rows=csv_iter()),mimetype='text/plain')

def serve_bin(hit,mimetype):
    hdr_path = binpid2path.resolve(pid=hit.bin_lid,format='hdr').value
    props = read_hdr(LocalFileSource(hdr_path))
    context = props[CONTEXT]
    del props[CONTEXT]
    # sort properties according to their order in the header schema
    props = [(k,props[k]) for k,_ in HDR_SCHEMA]
    # get a list of all targets, taking into account stitching
    targets = list_targets(hit)
    target_pids = ['%s_%05d' % (hit.bin_pid, target['targetNumber']) for target in targets]
    template = dict(hit=hit,context=context,properties=props,target_pids=target_pids)
    if minor_type(mimetype) == 'xml':
        return Response(render_template('bin.xml',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'rdf+xml':
        return Response(render_template('bin.rdf',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'csv':
        return bin2csv(hit,targets)
    elif mimetype == 'application/json':
        properties = dict(props)
        properties['context'] = context
        properties['targets'] = targets
        return jsonr(properties)
    else:
        abort(404)

def serve_target(hit,mimetype):
    target = get_target(hit.bin_lid, hit.target_no) # read the target from the ADC file
    # sort the target properties according to the order in the schema
    schema_keys = [k for k,_ in ADC_SCHEMA[hit.schema_version]]
    target = [(k,target[k]) for k in order_keys(target, schema_keys)]
    # now populate the template appropriate for the MIME type
    template = dict(hit=hit,target=target)
    if minor_type(mimetype) == 'xml':
        return Response(render_template('target.xml',**template), mimetype='text/xml')
    elif minor_type(mimetype) == 'rdf+xml':
        return Response(render_template('target.rdf',**template), mimetype='text/xml')
    elif mimetype == 'application/json':
        return jsonr(dict(target))
    print minor_type(mimetype)

def image_types(hit):
    # now determine PIL format and MIME type
    filename = '%s.%s' % (hit.lid, hit.extension)
    pil_format = filename2format(filename)
    (mimetype, _) = mimetypes.guess_type(filename)
    return (pil_format, mimetype)

def serve_roi(hit):
    """Serve a stitched ROI image given the output of the pid resolver"""
    # resolve the ADC and ROI files
    adc_path = binpid2path.resolve(pid=hit.bin_lid,format='adc').value
    roi_path = binpid2path.resolve(pid=hit.bin_lid,format='roi').value
    if app.config[STITCH]:
        limit=2 # read two targets, in case we need to stitch
    else:
        limit=1 # just read one
    targets = list(read_adc(LocalFileSource(adc_path),offset=hit.target_no-1,limit=limit))
    if len(targets) == 0: # no targets? return Not Found
        abort(404)
    # open the ROI file as we may need to read more than one
    with open(roi_path,'rb') as roi_file:
        if app.config[STITCH]:
            pairs = list(find_pairs(targets)) # look for stitched pairs
        else:
            pairs = targets
        if len(pairs) >= 1: # found one?
            (a,b) = pairs[0] # split pair
            images = list(read_rois((a,b),roi_file=roi_file)) # read the images
            (roi_image, mask) = stitch((a,b), images) # stitch them
        else:
            # now check that the target number is correct
            target = targets[0]
            if target[TARGET_NUMBER] != hit.target_no:
                abort(404)
            images = list(read_rois([target],roi_file=roi_file)) # read the image
            roi_image = images[0]
        sdfokjsdf
        # now determine PIL format and MIME type
        (pil_format, mimetype) = image_types(hit)
        # return the image data
        return image_response(roi_image,pil_format,mimetype)

if __name__=='__main__':
    port = 5061
    if len(sys.argv) > 1:
        config = get_config(sys.argv[1])
        try:
            configure(config)
        except KeyError:
            pass
        try:
            port = int(config.port)
        except KeyError:
            pass
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0',port=port)
