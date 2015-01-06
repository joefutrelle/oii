import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.files import parsed_pid2fileset, get_data_roots
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
        logging.warn('ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('waking up for %s' % wakeup_key)
    # acquire accession jobs, one at a time
    while True:
        client.expire() # let jobs expire so we can reacquire them
        r = client.start_next([ACCESSION_ROLE])
        if not isok(r): # no more jobs
            logging.warn('going back to sleep')
            return
        job = r.json()
        pid = job[PID]
        client.update(pid,ttl=30) # a generous time allocation
        try:
            parsed = parse_pid(pid)
            lid = parsed[LID]
            ts_label = parsed[TS_LABEL]
            roots = get_data_roots(session, ts_label) # get raw data roots
            fileset = parsed_pid2fileset(parsed, roots)
            fileset[LID] = lid
            session.expire_all() # don't be stale!
            acc = Accession(session,ts_label)
            logging.warn('ACCESSION %s' % pid)
            ret = acc.add_fileset(fileset)
            if ret:
                logging.warn('SUCCESS %s' % pid)
            else:
                logging.warn('FAIL/SKIP %s' % pid)
            client.update(pid, state='available', event='complete', message='accession completed',ttl=None)
            session.commit()
        except Exception as e:
            logging.warn('ERROR during accession for' % pid)
            client.update(pid, state='error', event='exception', message=str(e))
            # continue to next job
