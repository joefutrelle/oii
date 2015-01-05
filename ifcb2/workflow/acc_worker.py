import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.acquisition import do_copy
from oii.ifcb2.orm import Instrument

from oii.workflow.client import WorkflowClient, isok
from oii.workflow.async import async, wakeup_task
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, ACCESSION_ROLE
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

ACC_WAKEUP_KEY='ifcb:accession'

@wakeup_task
def acc_wakeup(wakeup_key):
    """- wake up and expire the session
    - ignore wakeup keys other than ACC_WAKEUP_KEY
    """
    # figure out if this wakeup matters to us
    if wakeup_key != ACC_WAKEUP_KEY:
        return
    # acquire next accession job
    r = client.start_next([ACCESSION_ROLE])
    if not isok(r):
        return
    job = r.json()
    pid = job[PID]
    parsed = parse_pid(pid)
    lid = parsed[LID]
    ts_label = parsed[TS_LABEL]
    #acc = Accession(session,ts_label)
    print 'timeseries %s, lid %s' % (ts_label, lid)
