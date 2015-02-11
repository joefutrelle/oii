import logging

from oii.ifcb2.identifiers import as_product, canonicalize
from oii.ifcb2.acquisition import do_copy
from oii.ifcb2.orm import Instrument
from oii.ifcb2.accession import Accession
from oii.ifcb2 import LID

from oii.workflow.client import WorkflowClient, Mutex, Busy
from oii.workflow.async import async, wakeup_task
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, BINZIP_PRODUCT
from oii.ifcb2.workflow import BLOBS_PRODUCT, FEATURES_PRODUCT, WEBCACHE_PRODUCT
from oii.ifcb2.workflow import WILD2RAW, RAW2BINZIP, BINZIP2BLOBS, BLOBS2FEATURES, BINZIP2WEBCACHE

### FIXME config this right
from oii.ifcb2.session import session

client = WorkflowClient()
TIME_SERIES='mock'
URL_PREFIX='http://128.128.14.19:8080/'

### end FIXME

def get_acc_key(time_series):
    """given an instrument name, return the acquisition key"""
    return 'ifcb:acc:%s' % time_series
    
def schedule_accession(client,pid):
    """use a oii.workflow.WorkflowClient to schedule an accession job for a fileset.
    pid must not be a local id--it must be namespace-scoped"""
    """dependencies:
    raw <- wild"""
    wild_pid = as_product(pid, WILD_PRODUCT)
    raw_pid = as_product(pid, RAW_PRODUCT)
    client.depend(raw_pid, wild_pid, WILD2RAW)

@wakeup_task
def acc_wakeup(wakeup_key):
    """- wake up and expire the session
    - acquire a mutex on the acquisition key
    - query for the instrument
    - run the copy job
    - schedule the accession job
    - wakeup accession workers"""
    # figure out if this wakeup matters to us
    acc_key = get_acc_key(TIME_SERIES)
    if wakeup_key != acc_key:
        return
    # attempt to acquire mutex. if fails, that's fine,
    # that means batch accession is already underway
    try:
        with Mutex(acc_key,ttl=45) as mutex:
            session.expire_all() # don't be stale!
            accession = Accession(session, TIME_SERIES)
            logging.warn('%s: scheduling batch accession' % TIME_SERIES)
            for fs in accession.list_filesets():
                pid = canonicalize(URL_PREFIX, TIME_SERIES, fs[LID])
                logging.warn('scheduling accession for %s' % pid)
                schedule_accession(client,pid)
                mutex.heartbeat()
            logging.warn('%s: batch accession scheduled' % TIME_SERIES)
            client.wakeup()
    except Busy:
        pass
