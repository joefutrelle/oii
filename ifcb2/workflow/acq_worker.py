import logging

from oii.ifcb2.identifiers import as_product
from oii.ifcb2.acquisition import do_copy
from oii.ifcb2.orm import Instrument

from oii.workflow.client import WorkflowClient, Mutex, Busy
from oii.workflow.async import async, wakeup_task
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, ACCESSION_ROLE
from oii.ifcb2.workflow import BIN_ZIP_ROLE, BIN_ZIP_PRODUCT
from oii.ifcb2.workflow import ACC_WAKEUP_KEY, BIN_ZIP_WAKEUP_KEY
from oii.ifcb2.workflow import WEBCACHE_ROLE

"""
Here's the deal.

Worker:
- configged with ORM session, name of instrument, and workflow client
- wake up and expire the session
- acquire a mutex on the acquisition key
- query for the instrument
- run the copy job
- schedule the accession job
- wakeup accession workers

Scheduled task:
- configged with a workflow client and the instrument name
- hit the "wakeup" endpoint with the acquisition key

Run worker as:
celery --config=oii.workflow.async_config -A oii.ifcb2.workflow.acq_worker worker -n acq_worker_mock
"""

### FIXME config this right
from oii.ifcb2.session import session

client = WorkflowClient()
instrument_name='mock'
URL_PREFIX='http://128.128.14.19:8080/'

### end FIXME

def get_acq_key(instrument_name):
    """given an instrument name, return the acquisition key"""
    return 'ifcb:acq:%s' % instrument_name
    
def schedule_accession(client,pid):
    """use a oii.workflow.WorkflowClient to schedule an accession job for a fileset.
    also schedule a downstream zip job.
    pid must not be a local id--it must be namespace-scoped"""
    wild_pid = as_product(pid,WILD_PRODUCT)
    raw_pid = as_product(pid,RAW_PRODUCT)
    client.depend(raw_pid, wild_pid, ACCESSION_ROLE)
    zip_pid = as_product(pid,BIN_ZIP_PRODUCT)
    client.depend(zip_pid, raw_pid, BIN_ZIP_ROLE)
    webcache_pid = as_product(pid,'webcache') # product label not important here
    client.depend(webcache_pid, zip_pid, WEBCACHE_ROLE)

def copy_work(instrument,callback=None):
    """what an acquisition worker does"""
    for lid in do_copy(instrument):
        if callback is not None:
            callback(lid)

@wakeup_task
def acq_wakeup(wakeup_key):
    """- wake up and expire the session
    - acquire a mutex on the acquisition key
    - query for the instrument
    - run the copy job
    - schedule the accession job
    - wakeup accession workers"""
    # figure out if this wakeup matters to us
    acq_key = get_acq_key(instrument_name)
    if wakeup_key != acq_key:
        return
    # attempt to acquire mutex. if fails, that's fine,
    # that means acquisition is aready underway
    try:
        with Mutex(acq_key,ttl=45) as mutex:
            # get the instrument info
            session.expire_all() # don't be stale!
            instrument = session.query(Instrument).\
                         filter(Instrument.name==instrument_name).\
                         first()
            if instrument is None:
                logging.warn('ERROR cannot find instrument named "%s"' % instrument_name)
                return
            ts_label = instrument.time_series.label
            logging.warn('%s: starting acquisition cycle' % instrument_name)
            def callback(lid):
                logging.warn('%s: copied %s from %s' % (ts_label, lid, instrument_name))
                mutex.heartbeat() # still alive
                # schedule an accession job and wake up accession workers
                pid = '%s%s/%s' % (URL_PREFIX, ts_label, lid)
                schedule_accession(client,pid)
                client.wakeup(ACC_WAKEUP_KEY) # wake up accession workers
                logging.warn('%s: scheduled accession for %s' % (ts_label, lid))
            copy_work(instrument, callback=callback)
            logging.warn('%s: acquisition cycle complete' % ts_label)
    except Busy:
        logging.warn('acquisition already underway for %s' % wakeup_key)
