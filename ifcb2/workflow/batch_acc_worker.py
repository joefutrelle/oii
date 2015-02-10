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
INSTRUMENT_NAME='mock'
URL_PREFIX='http://128.128.14.19:8080/'

### end FIXME

def get_acc_key(instrument_name):
    """given an instrument name, return the acquisition key"""
    return 'ifcb:acc:%s' % instrument_name
    
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
    acc_key = get_acc_key(INSTRUMENT_NAME)
    if wakeup_key != acc_key:
        return
    # attempt to acquire mutex. if fails, that's fine,
    # that means acquisition is aready underway
    try:
        with Mutex(acc_key,ttl=45) as mutex:
            # get the instrument info
            session.expire_all() # don't be stale!
            instrument = session.query(Instrument).\
                         filter(Instrument.name==INSTRUMENT_NAME).\
                         first()
            if instrument is None:
                logging.warn('ERROR cannot find instrument named "%s"' % INSTRUMENT_NAME)
                return
            ts_label = instrument.time_series.label
            accession = Accession(session, ts_label)
            logging.warn('%s: scheduling batch accession' % INSTRUMENT_NAME)
            for fs in accession.list_filesets():
                pid = canonicalize(URL_PREFIX, ts_label, fs[LID])
                logging.warn('scheduling accession for %s' % pid)
                schedule_accession(client,pid)
            logging.warn('%s: batch accession scheduled' % ts_label)
            client.wakeup()
    except Busy:
        pass
