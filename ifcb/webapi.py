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
roipid2no = rs['pid']

def configure(config):
    # FIXME populate app.config dict
    pass

app.config['NAMESPACE'] = 'http://demi.whoi.edu:5061/'

# utilities

def get_target(bin,target_no):
    adc_path = binpid2path.resolve(pid=bin,format='adc').value
    return read_target(LocalFileSource(adc_path), target_no)

def image_response(image,format,mimetype):
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/api/foo/<bar>')
def foo(bar):
    d = dict(a='foo', b=bar)
    return Response(render_template('foo.xml',d=d), mimetype='text/xml')

@app.route('/<time_series>/<path:pid>')
def resolve(time_series,pid):
    s = roipid2no.resolve(pid=pid)
    extension = s.extension
    if extension is None:
        extension = 'rdf'
    s.namespace = '%s%s/' % (app.config['NAMESPACE'], time_series)
    filename = '%s.%s' % (s.lid, s.extension)
    (mimetype, _) = mimetypes.guess_type(filename)
    if re.match(r'image/',mimetype):
        return serve_stitched_roi(s)
    elif s.target is not None and re.match(r'.*/xml',mimetype):
        tn = int(s.target)
        target = get_target(s.bin, tn)
        sample_pid = s.namespace + s.bin
        print 'sample_pid = %s' % sample_pid
        return Response(render_template('target.xml',pid=sample_pid,target=target), mimetype='text/xml')

def serve_stitched_roi(s):
    s = roipid2no.resolve(pid=pid)
    bin = s.bin
    target_no = int(s.target)
    extension = s.extension
    adc_path = binpid2path.resolve(pid=bin,format='adc').value
    roi_path = binpid2path.resolve(pid=bin,format='roi').value
    targets = list(read_adc(LocalFileSource(adc_path),offset=target_no-1,limit=5))
    if len(targets) == 0:
        abort(404)
    with open(roi_path,'rb') as roi_file:
        pairs = list(find_pairs(targets))
        if len(pairs) >= 1:
            (a,b) = pairs[0]
            images = list(read_rois((a,b),roi_file=roi_file))
            (roi_image, mask) = stitch((a,b), images)
        else:
            # now check that the target number is correct
            target = targets[0]
            if target[TARGET_NUMBER] != target_no:
                abort(404)
            # now check that there are pixels in this image's dimensions (exclude 0xX and Xx0 images)
            if target[HEIGHT] * target[WIDTH] == 0:
                abort(404)
            images = list(read_rois([target],roi_file=roi_file))
            roi_image = images[0]
        filename = '%s.%s' % (s.lid, s.extension)
        pil_format = filename2format(filename)
        (mimetype, _) = mimetypes.guess_type(filename)
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
