import sys
import os
from flask import Flask, Response, abort
from oii.webapi.image_service.stereo import get_img, get_resolver
from oii.webapi.image_service.utils import image_response
from oii.config import get_config
from oii.resolver import parse_stream
from skimage.transform import resize
from werkzeug.contrib.cache import SimpleCache

app = Flask(__name__)

# string key constants
CACHE='cache'
CACHE_TTL='cache_ttl'
RESOLVER='resolver'
PORT='port'

IMAGE_RESOLVER='image' # name of image resolver in resolvers

def pid2image(pid):
    hit = app.config[RESOLVER][IMAGE_RESOLVER].resolve(pid=pid)
    if hit is None:
        abort(404)
    return hit, get_img(hit)

@app.route('/data/<path:pid>')
@app.route('/<path:pid>')
@app.route('/data/width/<int:width>/<path:pid>')
@app.route('/width/<int:width>/<path:pid>')
def serve_image(width=None,pid=None):
    hit, img = pid2image(pid)
    if width is not None:
        (h,w) = img.shape[:2]
        height = int(1. * width / w * h)
        img = resize(img,(height,width))
    return image_response(img, pid)

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
