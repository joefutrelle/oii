import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.files import parsed_pid2fileset, get_data_roots
from oii.ifcb2.acquisition import do_copy
from oii.ifcb2.orm import Instrument

from oii.workflow import FOREVER, AVAILABLE, COMPLETED, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, WILD2RAW
from oii.ifcb2.accession import Accession

"""
Here's the deal.

Worker:
- configged with ORM session, workflow client, time series label
- wake up and expire the session

Scheduled task:
- configged with a workflow client and the time series label
- hit the "wakeup" endpoint with the acquisition key
"""

### FIXME config this right
from oii.ifcb2.session import session

client = WorkflowClient()

def do_acc(pid, job):
    logging.warn('ACCESSION %s' % pid)
    parsed = parse_pid(pid)
    lid = parsed[LID]
    ts_label = parsed[TS_LABEL]
    roots = get_data_roots(session, ts_label) # get raw data roots
    fileset = parsed_pid2fileset(parsed, roots)
    fileset[LID] = lid
    session.expire_all() # don't be stale!
    acc = Accession(session,ts_label)
    client.update(pid,ttl=60) # allow 60s for accession
    ret = acc.add_fileset(fileset)
    if ret:
        logging.warn('SUCCESS %s' % pid)
    else:
        logging.warn('FAIL %s' % pid)
        raise Exception('accession failed')
    session.commit()
    client.wakeup()

@wakeup_task
def acc_wakeup(ignore):
    """- wake up and expire the session
    """
    client.do_all_work([WILD2RAW],do_acc,'accession complete')
