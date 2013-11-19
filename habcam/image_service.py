from flask import Flask, request, url_for, abort, session, Response, render_template
import json
import re
import sys
import os
import tempfile
from io import BytesIO
from skimage import img_as_float
from skimage.io import imread
from skimage.color import rgb2gray
from skimage.transform import resize
import shutil
from StringIO import StringIO
from oii.config import get_config
from oii.times import iso8601
from oii.webapi.utils import jsonr
from oii.image.pil.utils import filename2format, thumbnail
import urllib
from oii.utils import order_keys, change_extension, remove_extension
from oii.resolver import parse_stream
from oii.iopipes import UrlSource, LocalFileSource
from oii.image.pil.utils import filename2format, thumbnail
from oii.habcam.metadata import Metadata
from oii.image.demosaic import demosaic
from oii.habcam.lightfield import quick
import mimetypes
from PIL import Image
from werkzeug.contrib.cache import SimpleCache

app = Flask(__name__)
#app.debug = True

# importantly, set max-age on static files (e.g., javascript) to something really short
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30

# string key constants
CACHE='cache'
CACHE_TTL='cache_ttl'
RESOLVER='resolver'
PORT='port'
METADATA='psql_connect'

# resolver names
PID='pid' # splits id into parts
IMAGE='image' # finds image data for a given imagename
BIN='bin_pid' # parses bin pids
IMGDATA='imgdata' # finds .img files
PID2RGB='pid2rgb' # finds _rgb_illum_LRs (used in localpath endpoint)

def configure(config=None):
    app.config[CACHE] = SimpleCache()
    app.config[CACHE_TTL] = 120
    try:
        if config.debug in ['True', 'true', 'T', 't', 'Yes', 'yes', 'debug']:
            app.debug = True
    except AttributeError:
        pass
    try:
        app.config[RESOLVER] = parse_stream(config.resolver)
    except AttributeError:
        app.config[RESOLVER] = parse_stream('oii/habcam/image_resolver.xml')
    try:
        app.config[PORT] = int(config.port)
    except:
        app.config[PORT] = 5061
    app.config[METADATA] = Metadata(config)

def major_type(mimetype):
    return re.sub(r'/.*','',mimetype)

def minor_type(mimetype):
    return re.sub(r'.*/','',mimetype)

def image_types(filename):
    # now determine PIL format and MIME type
    pil_format = filename2format(filename)
    (mimetype, _) = mimetypes.guess_type(filename)
    return (pil_format, mimetype)

def image_response(image,format,mimetype):
    """Construct a Flask Response object for the given image, PIL format, and MIME type."""
    buf = StringIO()
    if format == 'JPEG':
        im = image.save(buf,format,quality=85)
    else:
        im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

# product workflow
def cfa_LR(fin):
    return img_as_float(imread(fin,plugin='freeimage'))
def cfa_illum_LR(fin):
    return img_as_float(imread(fin,plugin='freeimage'))
def rgb_illum_LR(fin):
    return img_as_float(imread(fin,plugin='freeimage'))
def rgb_illum_L(fin,pattern='rggb'):
    lr = rgb_illum_LR(fin)
    (_,w,_) = lr.shape
    return lr[:,:w/2,:]
def rgb_illum_R(fin):
    lr = rgb_illum_LR(fin)
    (_,w,_) = lr.shape
    return lr[:,w/2:,:]
def y_illum_LR(fin):
    return rgb2gray(rgb_illum_LR(fin))
def redcyan(fin):
    return quick.redcyan(y_illum_LR(fin),downscale=4)

@app.route('/localpath/<imagename>')
def serve_localpath(imagename=None):
    resolver = app.config[RESOLVER]
    hit = resolver[PID2RGB].resolve(pid=imagename)
    if hit is None:
        abort(404)
    return Response(hit.value+'\n', mimetype='text/plain')

@app.route('/imgdata/<imagename>')
def serve_imgdata(imagename=None):
    resolver = app.config[RESOLVER]
    hit = resolver[IMGDATA].resolve(pid=imagename)
    imagename = remove_extension(imagename)
    if hit is None:
        abort(404)
    with open(hit.value,'r') as csvin:
        for line in csvin:
            imgname = remove_extension(re.split(',',line)[0].strip())
            if imgname == imagename:
                return Response(line, mimetype='text/plain')
    abort(404)

@app.route('/width/<int:width>/<imagename>')
@app.route('/<imagename>')
def serve_image(width=None,imagename=None):
    resolver = app.config[RESOLVER]
    (hit,out) = (resolver[IMAGE].resolve(pid=imagename), None)
    print hit
    if hit is not None:
        if hit.extension == 'json':
            return Response(app.config[METADATA].json(imagename), mimetype='application/json')
        fin = hit.value
        (format, mimetype) = image_types(hit.filename)
        if hit.product is None:
            out = img_as_float(imread(fin))
    if out is None:
        if hit.product == 'rgb_illum_LR':
            out = rgb_illum_LR(fin)
        if hit.product == 'rgb_illum_L':
            out = rgb_illum_L(fin)
        if hit.product == 'rgb_illum_R':
            out = rgb_illum_R(fin)
        if hit.product == 'redcyan':
            out = redcyan(fin)
    if out is None:
        hit = resolver[BIN].resolve(pid=imagename)
        if hit is not None and hit.extension == 'json':
            return Response(app.config[METADATA].json_bin(hit.bin_lid), mimetype='application/json')
        hit = resolver[PID].resolve(pid=imagename)
        (format, mimetype) = image_types(hit.filename)
        if hit is None:
            abort(404)
        fin = resolver[IMAGE].resolve(pid=change_extension(hit.imagename,'tif')).value
        if hit.product == 'redcyan':
            out = redcyan(fin,pattern='rggb')
    if out is not None:
        if width is not None:
            (h,w) = (out.shape[0], out.shape[1])
            height = int(1. * width / w * h) #int((width/float(w)) * h)
            out = resize(out,(height,width))
        img = Image.fromarray((out * 255).astype('uint8'))
        return image_response(img, format, mimetype)
    # nothing worked
    abort(404)

# utilities
if __name__=='__main__':
    """First argument is a config file"""
    if len(sys.argv) > 1:
        configure(get_config(sys.argv[1]))
    else:
        configure()
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0',port=app.config[PORT])
else:
    config = get_config(os.environ['IMAGE_SERVICE_CONFIG_FILE'])
    configure(config)

