from flask import Flask, request, url_for, abort, session, Response, render_template
from unittest import TestCase
import json
import re
import sys
import os
from StringIO import StringIO
from oii.config import get_config
from oii.times import iso8601
from oii.webapi.utils import jsonr
import urllib
from oii.ifcb.formats.adc import read_adc, read_target, TARGET_NUMBER, WIDTH, HEIGHT
from oii.ifcb.formats.roi import read_roi, read_rois
from oii.resolver import parse_stream
from oii.ifcb.stitching import find_pairs, stitch
from oii.io import UrlSource, LocalFileSource
from oii.image.pil.utils import filename2format
import mimetypes

app = Flask(__name__)
app.debug = True

# importantly, set max-age on static files (e.g., javascript) to something really short
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30
rs = parse_stream('oii/ifcb/mvco.xml')
binpid2path = rs['binpid2path']
pid_resolver = rs['pid']

def configure(config):
    # FIXME populate app.config dict
    pass

app.config['NAMESPACE'] = 'http://demi.whoi.edu:5061/'

# utilities

def get_target(bin,target_no):
    """Read a single target from an ADC file given the bin PID/LID and target number"""
    adc_path = binpid2path.resolve(pid=bin,format='adc').value
    return read_target(LocalFileSource(adc_path), target_no)

def image_response(image,format,mimetype):
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/api/foo/<bar>')
def foo(bar):
    d = dict(a='foo', b=bar)
    return Response(render_template('foo.xml',d=d), mimetype='text/xml')

@app.route('/<time_series>/<path:lid>')
def resolve(time_series,lid):
    """Resolve a URL to some data endpoint in a time series, including bin and target metadata endpoints,
    and image endpoints"""
    # use the PID resolver (which also works for LIDs)
    s = pid_resolver.resolve(pid=lid)
    # construct the namespace from the configuration and time series ID
    s.namespace = '%s%s/' % (app.config['NAMESPACE'], time_series)
    # determine extension
    if s.extension is None: # default is .rdf
        s.extension = 'rdf'
    # determine MIME type
    filename = '%s.%s' % (s.lid, s.extension)
    (mimetype, _) = mimetypes.guess_type(filename)
    # is the user requesting an image?
    if re.match(r'image/',mimetype):
        return serve_stitched_roi(s)
    else:
        if s.target is not None: # is this a target endpoint (rather than a bin endpoint?)
            tn = int(s.target)
            target = get_target(s.bin, tn) # read the target from the ADC file
            target_pid = s.namespace + s.lid
            bin_pid = s.namespace + s.bin
            # now populate the template appropriate for the MIME type
            if re.match(r'.*/xml',mimetype):
                return Response(render_template('target.xml',pid=target_pid,target=target), mimetype='text/xml')
            elif re.match(r'.*/rdf',mimetype):
                return Response(render_template('target.rdf',pid=target_pid,target=target,bin=bin_pid), mimetype='text/xml')
    # nothing recognized, so return Not Found
    abort(404)

def serve_stitched_roi(s):
    """Serve a stitched ROI image given the output of the pid resolver"""
    target_no = int(s.target) # parse target number
    # resolve the ADC and ROI files
    adc_path = binpid2path.resolve(pid=s.bin,format='adc').value
    roi_path = binpid2path.resolve(pid=s.bin,format='roi').value
    # read two targets, in case we need to stitch
    targets = list(read_adc(LocalFileSource(adc_path),offset=target_no-1,limit=2))
    if len(targets) == 0: # no targets? return Not Found
        abort(404)
    # open the ROI file as we may need to read more than one
    with open(roi_path,'rb') as roi_file:
        pairs = list(find_pairs(targets)) # look for stitched pairs
        if len(pairs) >= 1: # found some?
            (a,b) = pairs[0] # assume there's just one
            images = list(read_rois((a,b),roi_file=roi_file)) # read the images
            (roi_image, mask) = stitch((a,b), images) # stitch them
        else:
            # now check that the target number is correct
            target = targets[0]
            if target[TARGET_NUMBER] != target_no:
                abort(404)
            # now check that there are pixels in this image's dimensions (exclude 0xX and Xx0 images)
            if target[HEIGHT] * target[WIDTH] == 0:
                abort(404)
            images = list(read_rois([target],roi_file=roi_file)) # read the image
            roi_image = images[0]
        # now determine PIL format and MIME type
        filename = '%s.%s' % (s.lid, s.extension)
        pil_format = filename2format(filename)
        (mimetype, _) = mimetypes.guess_type(filename)
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
