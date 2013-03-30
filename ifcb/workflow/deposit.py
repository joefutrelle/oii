import json
import os
import sys
from time import time, strftime, gmtime
from math import floor
import shutil
from StringIO import StringIO

from flask import Flask, abort, request, Response

from oii.utils import gen_id
from oii.config import get_config
from oii.resolver import parse_stream

RESOLVER='resolver'
PORT='port'

app = Flask(__name__)
app.debug = True

def jsonr(s):
    return Response(json.dumps(s), mimetype='application/json')

def iso8601utcnow():
    t = time()
    ms = int(floor((t * 1000) % 1000))
    return '%s.%03dZ' % (strftime('%Y-%m-%dT%H:%M:%S',gmtime(t)),ms)

blob_resolver = None # configged below
blob_destination = None # configged below

@app.route('/deposit/<product>/<path:pid>',methods=['POST'])
def deposit_impl(product,pid):
    if product == 'blobs':
        try:
            destpath = blob_destination.resolve(pid=pid).value
        except:
            abort(500)
    else:
        abort(404)
    product_data = request.data
    destpath_part = '%s_%s.part' % (destpath, gen_id())
    try:
        os.makedirs(os.path.dirname(destpath))
    except:
        pass
    with open(destpath_part,'w') as out:
        shutil.copyfileobj(StringIO(product_data), out)
    os.rename(destpath_part, destpath)
    utcnow = iso8601utcnow()
    message = '%s wrote %d bytes to %s' % (utcnow, len(product_data), destpath)
    return jsonr(dict(
        status='OK',
        time=utcnow,
        message=message,
        pid=pid,
        path=destpath
    ))

@app.route('/exists/<product>/<path:pid>')
def exists_impl(product,pid):
    if product == 'blobs':
        exists = False
        try:
            destpath = blob_destination.resolve(pid=pid).value
        except:
            abort(500)
        exists = os.path.exists(destpath)
    else:
        abort(404)
    if exists:
        message = '%s %s FOUND at %s' % (iso8601utcnow(), pid, destpath)
    else:
        message = '%s %s NOT FOUND' % (iso8601utcnow(), pid)
    utcnow = iso8601utcnow()
    return jsonr(dict(
        exists=exists,
        time=utcnow,
        message=message,
        pid=pid,
        path=destpath
    ))

def configure(config=None):
    app.config[RESOLVER] = config.resolver
    try:
        if config.debug in ['True', 'true', 'T', 't', 'Yes', 'yes', 'debug']:
            app.debug = True
    except:
        pass
    try:
        app.config[PORT] = int(config.port)
    except:
        app.config[PORT] = 5063

if __name__=='__main__':
    if len(sys.argv) > 1:
        configure(get_config(sys.argv[1]))
    else:
        configure()
else:
    configure(get_config(os.environ['DEPOSIT_CONFIG_FILE']))

rs = parse_stream(app.config[RESOLVER])
blob_resolver = rs['mvco_blob']
blob_destination = rs['blobs']

if __name__=='__main__':
    app.run(host='0.0.0.0',port=app.config[PORT])
