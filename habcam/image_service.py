from flask import Flask, request, url_for, abort, session, Response, render_template
import json
import re
import sys
import os
import tempfile
from io import BytesIO
import shutil
from StringIO import StringIO
from oii.config import get_config
from oii.times import iso8601
from oii.webapi.utils import jsonr
from oii.image.pil.utils import filename2format, thumbnail
import urllib
from oii.utils import order_keys
from oii.resolver import parse_stream
from oii.iopipes import UrlSource, LocalFileSource
from oii.image.pil.utils import filename2format, thumbnail
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

# resolver names
PID='pid'
IMAGE='image'

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
    im = image.save(buf,format)
    return Response(buf.getvalue(), mimetype=mimetype)

@app.route('/data/<imagename>')
def serve_image(imagename):
    resolver = app.config[RESOLVER]
    app.logger.debug(imagename)
    # FIXME debug
    for s in resolver[IMAGE].resolve_all(pid=imagename):
        app.logger.debug(str(s))
    # end debug
    hit = resolver[IMAGE].resolve(pid=imagename)
    if hit is not None:
        pathname = hit.value
        (format, mimetype) = image_types(hit.filename)
        if mimetype == 'image/tiff':
            return Response(file(pathname), direct_passthrough=True, mimetype=mimetype)
        else:
            return image_response(Image.open(pathname), format, mimetype)
    else:
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
    config = get_config(os.environ['HABCAM_CONFIG_FILE'])
    configure(config)

