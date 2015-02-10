import logging

from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.identifiers import as_product, parse_pid
from oii.ifcb2.files import parsed_pid2fileset, get_data_roots
from oii.ifcb2.acquisition import do_copy
from oii.ifcb2.orm import Instrument

from oii.workflow import FOREVER, AVAILABLE, COMPLETED, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

from oii.ifcb2.accession import Accession
from oii.ifcb2.workflow import WILD_PRODUCT, RAW_PRODUCT, WILD2RAW, BINZIP_PRODUCT
from oii.ifcb2.workflow import BLOBS_PRODUCT, FEATURES_PRODUCT, WEBCACHE_PRODUCT
from oii.ifcb2.workflow import WILD2RAW, RAW2BINZIP, BINZIP2BLOBS, BLOBS2FEATURES, BINZIP2WEBCACHE

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

def schedule_products(pid, client):
    """dependencies:
    features <- blobs <- binzip <- raw <- wild"""
    raw_pid = as_product(pid, RAW_PRODUCT)
    binzip_pid = as_product(pid, BINZIP_PRODUCT)
    client.depend(binzip_pid, raw_pid, RAW2BINZIP)
    webcache_pid = as_product(pid, WEBCACHE_PRODUCT)
    client.depend(webcache_pid, binzip_pid, BINZIP2WEBCACHE)
    blobs_pid = as_product(pid, BLOBS_PRODUCT)
    client.depend(blobs_pid, binzip_pid, BINZIP2BLOBS)
    features_pid = as_product(pid, FEATURES_PRODUCT)
    client.depend(features_pid, blobs_pid, BLOBS2FEATURES)

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
    schedule_products(pid, client)
    client.wakeup()

@wakeup_task
def acc_wakeup(ignore):
    """- wake up and expire the session
    """
    client.do_all_work(
        roles=[WILD2RAW],
        callback=do_acc,
        ttl=40,
        message='accession complete')
