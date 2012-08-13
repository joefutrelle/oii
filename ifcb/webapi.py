from flask import Flask, request, url_for, abort, session, Response
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
from oii.ifcb.formats.adc import read_adc, TARGET_NUMBER, WIDTH, HEIGHT
from oii.ifcb.formats.roi import read_roi, read_rois
from oii.resolver import parse_stream
from oii.ifcb.stitching import find_pairs, stitch
from oii.io import UrlSource, LocalFileSource

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

def image_response(image,format,mimetype):
    buf = StringIO()
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/mvco/<path:pid>')
def serve_stitched_roi(pid):
    s = roipid2no.resolve(pid=pid)
    bin = s.bin
    target_no = int(s.target)
    adc_path = binpid2path.resolve(pid=bin,format='adc').value
    roi_path = binpid2path.resolve(pid=bin,format='roi').value
    targets = list(read_adc(LocalFileSource(adc_path),offset=target_no-1,limit=2))
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
        return image_response(roi_image,'jpeg','image/jpeg')

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
