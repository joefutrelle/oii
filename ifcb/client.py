# web service client for IFCB web services
from urllib2 import urlopen
import json
from oii.times import iso8601
from PIL import Image
from cStringIO import StringIO

def fetch_object(pid):
    return json.load(urlopen(pid+'.json'))

def list_targets(bin_pid):
    return fetch_object(bin_pid)['targets']

def list_bins(date=iso8601(),namespace='http://ifcb-data.whoi.edu/mvco/',n=25):
    return json.load(urlopen('%srss.py?format=json&date=%s&n=%d' % (namespace,date,n)))

def fetch_image(image_pid):
    return Image.open(StringIO(urlopen(image_pid+'.png').read()))