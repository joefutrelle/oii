from oii.workflow.async import wakeup_task
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, ACCESSION_ROLE
from oii.ifcb2.session import session

"""
Here's the deal.

Worker:
- configged with ORM session, name of instrument, acquisition key, and workflow client
- wake up and expire the session
- query for the instrument
- run the copy job
- schedule the accession job
- wakeup accession workers

Scheduled task:
- configged with a workflow client and the acquisition key
- hit the "wakeup" endpoint with the acquisition key
"""

def schedule_accession(client,pid):
    """use a oii.workflow.WorkflowClient to schedule an accession job for a fileset.
    pid must not be a local id--it must be namespace-scoped"""
    wild_pid = as_product(pid,WILD_PRODUCT)
    raw_pid = as_product(pid,RAW_PRODUCT)
    client.depend(raw_pid, wild_pid, ACCESSION_ROLE)

def copy_work(instrument,client,callback=None):
    """what an acquisition worker does"""
    ts_label = instrument.time_series.label
    for lid in do_copy(instrument):
        pid = '%s/%s' % (ts_label, lid)
        schedule_accession(client,pid)
        client.wakeup(ACCESSION_ROLE)
        if callback is not None:
            callback(lid)
