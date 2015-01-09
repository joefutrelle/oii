import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.workflow import BIN_ZIP_ROLE

from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
#from oii.ifcb2.session import session

client = WorkflowClient()

BIN_ZIP_WAKEUP_KEY='ifcb:bin_zip'

@wakeup_task
def bin_zip_wakeup(wakeup_key):
    if wakeup_key != BIN_ZIP_WAKEUP_KEY:
        logging.warn('ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('waking up for %s' % wakeup_key)
    for job in client.start_all([BIN_ZIP_ROLE]):
        pid = job[PID]
        logging.warn('MOCK completing job %s' % job)
        client.update(pid, state='available', event='complete', message='zip completed')
