import json
import urllib2 as urllib

class BlobDeposit(object):
    def __init__(self,url_base='http://localhost:5000'):
        self.url_base = url_base

    def exists(self,pid):
        req = urllib.Request('%s/exists/blobs/%s' % (self.url_base, pid))
        resp = json.loads(urllib.urlopen(req).read())
        return resp['exists']

    def deposit(self,pid,zipfile):
        with open(zipfile,'r') as inzip:
            zipdata = inzip.read()
            req = urllib.Request('%s/deposit/blobs/%s' % (self.url_base, pid), zipdata)
            req.add_header('Content-type','application/x-ifcb-blobs')
            resp = json.loads(urllib.urlopen(req).read())
            return resp
