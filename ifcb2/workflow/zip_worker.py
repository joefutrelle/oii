import logging

import tempfile
import requests

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE, BIN_LID
from oii.ifcb2.workflow import BIN_ZIP_ROLE, BIN_ZIP_WAKEUP_KEY
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.represent import binpid2zip

from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
from oii.ifcb2.session import session

client = WorkflowClient()

@wakeup_task
def bin_zip_wakeup(wakeup_key):
    if wakeup_key != BIN_ZIP_WAKEUP_KEY:
        logging.warn('BINZIP ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('BINZIP waking up for %s' % wakeup_key)
    for job in client.start_all([BIN_ZIP_ROLE]):
        pid = job[PID]
        parsed = parse_pid(pid)
        try:
            logging.warn('BINZIP creating zipfile for %s' % pid)
            with tempfile.NamedTemporaryFile() as zip_tmp:
                zip_path = zip_tmp.name
                binpid2zip(pid, zip_path)
                # construct binzip URL
                binzip_url = '%s%s_binzip.zip' % (parsed[NAMESPACE], parsed[BIN_LID])
                logging.warn('BINZIP depositing %s' % binzip_url)
                with open(zip_path,'rb') as zin:
                    requests.put(binzip_url, data=zin)
                client.complete(
                    pid,
                    state='available',
                    event='completed',
                    message='pretended to deposit %s' % binzip_url)
                logging.warn('BINZIP finished %s' % pid)
        except Exception as e:
            logging.warn('ERROR during zip for %s' % pid)
            client.complete(
                pid,
                state='error',
                event='exception',
                message=str(e))
