from flask import Flask, url_for, Response, request
import shutil
from StringIO import StringIO
from ifcb.util import iso8601utcnow
import sys
import os
import json
import urllib2 as urllib
import re
import tempfile

STORAGE='STORAGE'

app = Flask(__name__)
app.debug = True

def jsonr(s):
    return Response(json.dumps(s), mimetype='application/json')

@app.route('/deposit/<path:pid>',methods=['POST'])
def deposit_impl(pid):
    deposit_data = request.data
    destpath = app.config[STORAGE].dest(pid)
    try:
        os.makedirs(os.path.dirname(destpath))
    except:
        pass
    with open(destpath,'w') as out:
        shutil.copyfileobj(StringIO(deposit_data), out)
    utcnow = iso8601utcnow()
    message = '%s wrote %d bytes to %s' % (utcnow, len(deposit_data), destpath)
    return jsonr(dict(
        status='OK',
        time=utcnow,
        message=message,
        pid=pid,
        path=destpath
    ))
                     
@app.route('/exists/<path:pid>')
def exists_impl(pid):
    destpath = app.config[STORAGE].dest(pid)
    exists = app.config[STORAGE].exists(pid)
    if exists:
        message = '%s %s FOUND at %s' % (iso8601utcnow(), pid, destpath)
    else:
        message = '%s %s NOT FOUND at %s' % (iso8601utcnow(), pid, destpath)
    utcnow = iso8601utcnow()
    return jsonr(dict(
        exists=exists,
        time=utcnow,
        message=message,
        pid=pid,
        path=destpath
    ))

# client code

class Deposit(object):
    def __init__(self,url_base='http://localhost:5000'):
        self.url_base = url_base

    def exists(self,pid):
        req = urllib.Request('%s/exists/%s' % (self.url_base, pid))
        resp = json.loads(urllib.urlopen(req).read())
        return resp['exists']

    def deposit(self,pid,data_file):
        with open(data_file,'r') as indata:
            data = indata.read()
            req = urllib.Request('%s/deposit/%s' % (self.url_base, pid), data)
            req.add_header('Content-type','application/x-oii-deposit')
            resp = json.loads(urllib.urlopen(req).read())
            return resp

class Storage(object):
    def __init__(self,config=None):
        pass
    def dest(self,pid):
        return '/tmp/foo.txt'
    def local_exists(self,pid):
        return os.path.exists(self.dest(pid))
    def exists(self,pid):
        return self.local_exists(pid)

class DirectoryStorage(Storage):
    def __init__(self,config=None,key='product_directory'):
        if config is None:
            self.directory = tempfile.gettempdir()
        else:
            self.directory = getattr(config,key)
    def dest(self,pid):
        return os.path.join(self.directory,pid)

if __name__=='__main__':
    app.config[STORAGE] = 'whatevs'
    (h,p) = re.match(r'http://(.*):(\d+)',config.blob_deposit).groups()
    app.run(host=h, port=int(p))
