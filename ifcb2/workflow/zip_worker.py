import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.workflow import BIN_ZIP_ROLE, BIN_ZIP_WAKEUP_KEY

from oii.workflow import FOREVER
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
#from oii.ifcb2.session import session

client = WorkflowClient()

@wakeup_task
def bin_zip_wakeup(wakeup_key):
    if wakeup_key != BIN_ZIP_WAKEUP_KEY:
        logging.warn('BINZIP ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('BINZIP waking up for %s' % wakeup_key)
    for job in client.start_all([BIN_ZIP_ROLE]):
        pid = job[PID]
        logging.warn('BINZIP MOCK completing job %s' % job)
        client.update(
            pid,
            state='available',
            event='complete',
            message='zip mock completed',
            ttl=FOREVER)
