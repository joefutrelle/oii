import logging
from StringIO import StringIO
import shutil

import tempfile
import requests

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE, BIN_LID
from oii.ifcb2.workflow import WEBCACHE_PRODUCT, BINZIP2WEBCACHE
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.represent import binpid2zip

from oii.workflow import COMPLETED, AVAILABLE, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
client = WorkflowClient()

def do_webcache(pid,job):
    parsed = parse_pid(pid)
    bin_pid = ''.join([parsed[NAMESPACE], parsed[BIN_LID]])
    mosaic_base_url = '%sapi/mosaic/size/800x600/scale/0.33/page/1' % parsed[NAMESPACE]
    mosaic_json = '%s/%s.json' % (mosaic_base_url, bin_pid)
    mosaic_jpg = '%s/%s.jpg' % (mosaic_base_url, bin_pid)
    logging.warn('WEBCACHE hitting %s' % mosaic_json)
    r1 = requests.get(mosaic_json)
    json = r1.json() # read it, and throw it away
    logging.warn('WEBCACHE hitting %s' % mosaic_jpg)
    r2 = requests.get(mosaic_jpg)
    img_data = StringIO(r2.content) # read it, and throw it away
    logging.warn('WEBCACHE done for %s' % pid)

@wakeup_task
def webcache_wakeup(wakeup_key):
    client.do_all_work(
        roles=[BINZIP2WEBCACHE],
        callback=do_webcache,
        ttl=37,
        message='hit webcache URLs')
