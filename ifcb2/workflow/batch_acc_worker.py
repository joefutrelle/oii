import logging
import time

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
URL_PREFIX='http://128.128.14.19:8080/'

### end FIXME

def is_acc_key(key):
    return key is not None and key.startswith('ifcb:acc:')

def get_time_series(acc_key):
    return acc_key.split(':')[2]

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
    if not is_acc_key(wakeup_key):
        return
    time_series = get_time_series(wakeup_key)
    # attempt to acquire mutex. if fails, that's fine,
    # that means batch accession is already underway
    try:
        then = time.time()
        count = 0
        with Mutex(wakeup_key,ttl=45) as mutex:
            session.expire_all() # don't be stale!
            accession = Accession(session, time_series)
            logging.warn('%s: scheduling batch accession' % time_series)
            for fs in accession.list_filesets(): # FIXME debug, do all
                pid = canonicalize(URL_PREFIX, time_series, fs[LID])
                count += 1
                if count % 100 == 0:
                    logging.warn('%s: scheduled %d bins for accession' % (time_series, count))
                schedule_accession(client,pid)
                elapsed = time.time() - then
                if elapsed > 25: # don't send heartbeats too often
                    mutex.heartbeat() # retain mutex
                    then = time.time()
                client.wakeup() # wakeup workers
            logging.warn('%s: batch accession scheduled' % time_series)
            client.wakeup()
    except Busy:
        pass
