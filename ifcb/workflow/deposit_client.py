import sys
import urllib2 as urllib
import json

class Deposit(object):
    def __init__(self,url_base='http://localhost:5000',product_type='blobs'):
        self.url_base = url_base
        self.product_type = product_type

    def exists(self,pid):
        req = urllib.Request('%s/exists/%s/%s' % (self.url_base, self.product_type, pid))
        resp = json.loads(urllib.urlopen(req).read())
        return resp['exists']

    def deposit(self,pid,product_file):
        with open(product_file,'r') as inproduct:
            product_data = inproduct.read()
            req = urllib.Request('%s/deposit/%s/%s' % (self.url_base, self.product_type, pid), product_data)
            req.add_header('Content-type','application/x-ifcb-blobs')
            resp = json.loads(urllib.urlopen(req).read())
            return resp
        
if __name__=='__main__':
    d = Deposit('http://localhost:5063')
    zipfile = 'IFCB5_2013_088_666666_blobs_v2.zip'
    pid = 'http://ifcb-data.whoi.edu/mvco/IFCB5_2013_088_666666'
    d.deposit(pid,zipfile)

