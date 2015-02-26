import logging
import tempfile
import requests

from oii.ioutils import upload, exists

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE, BIN_LID
from oii.ifcb2.workflow import RAW2BINZIP
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.represent import binpid2zip

from oii.workflow import COMPLETED, AVAILABLE, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
client = WorkflowClient()

def do_binzip(pid, job):
    def log_callback(msg):
        logging.warn('BINZIP %s' % msg)
        client.heartbeat(pid,message=msg)
    parsed = parse_pid(pid)
    binzip_url = '%s%s_binzip.zip' % (parsed[NAMESPACE], parsed[BIN_LID])
    if exists(binzip_url):
        log_callback('skipping %s - binzip exists' % pid)
        return
    log_callback('BINZIP creating zipfile for %s' % pid)
    with tempfile.NamedTemporaryFile() as zip_tmp:
        zip_path = zip_tmp.name
        binpid2zip(pid, zip_path)
        # construct binzip URL
        log_callback('BINZIP depositing %s' % binzip_url)
        upload(zip_path, binzip_url)
    log_callback('BINZIP deposited %s' % binzip_url)
    client.wakeup()

@wakeup_task
def binzip_wakeup(wakeup_key):
    client.do_all_work(
        roles=[RAW2BINZIP],
        callback=do_binzip,
        ttl=217,
        message='deposited bin zip')
