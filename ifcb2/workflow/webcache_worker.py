import logging
from StringIO import StringIO
import shutil

import tempfile
import requests

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE, BIN_LID
from oii.ifcb2.workflow import WEBCACHE_ROLE, WEBCACHE_WAKEUP_KEY
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.represent import binpid2zip

from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
client = WorkflowClient()

@wakeup_task
def webcache_wakeup(wakeup_key):
    if wakeup_key != WEBCACHE_WAKEUP_KEY:
        logging.warn('WEBCACHE ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('WEBCACHE waking up for %s' % wakeup_key)
    for job in client.start_all([WEBCACHE_ROLE]):
        pid = job[PID]
        parsed = parse_pid(pid)
        try:
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
            client.complete(
                pid,
                state='available',
                event='completed',
                message='hit cache URLs')
        except Exception as e:
            logging.warn('webcache ERROR webcache for %s' % pid)
            client.complete(
                pid,
                state='error',
                event='exception',
                message=str(e))
