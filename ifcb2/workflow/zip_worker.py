import logging

import tempfile
import requests

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE, BIN_LID
from oii.ifcb2.workflow import BIN_ZIP_ROLE, BIN_ZIP_WAKEUP_KEY, WEBCACHE_WAKEUP_KEY
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.represent import binpid2zip

from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
client = WorkflowClient()

#### FIXME for random fail test
import random

@wakeup_task
def bin_zip_wakeup(wakeup_key):
    for job in client.start_all([BIN_ZIP_ROLE]):
        pid = job[PID]
        parsed = parse_pid(pid)
        try:
            logging.warn('BINZIP creating zipfile for %s' % pid)
            with tempfile.NamedTemporaryFile() as zip_tmp:
                zip_path = zip_tmp.name
                ## FIXME random fail test
                if random.random() < 0.1:
                    raise Exception('random failure')
                ## end fixme
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
                    message='deposited')
                logging.warn('BINZIP finished %s' % pid)
                client.wakeup(WEBCACHE_WAKEUP_KEY)
        except Exception as e:
            logging.warn('ERROR during zip for %s' % pid)
            client.complete(
                pid,
                state='error',
                event='exception',
                message=str(e))
