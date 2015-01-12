import logging

from oii.ifcb2 import get_resolver
from oii.ifcb2 import PID, LID, TS_LABEL
from oii.ifcb2.files import get_data_roots, get_product_destination
from oii.ifcb2.workflow import BIN_ZIP_ROLE, BIN_ZIP_WAKEUP_KEY
from oii.ifcb2.identifiers import as_product, parse_pid

from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

### FIXME config this right
from oii.ifcb2.session import session

client = WorkflowClient()

@wakeup_task
def bin_zip_wakeup(wakeup_key):
    if wakeup_key != BIN_ZIP_WAKEUP_KEY:
        logging.warn('BINZIP ignoring %s, sleeping' % wakeup_key)
        return
    logging.warn('BINZIP waking up for %s' % wakeup_key)
    for job in client.start_all([BIN_ZIP_ROLE]):
        pid = job[PID]
        try:
            zip_path = get_product_destination(session, pid, 'binzip')
            logging.warn('zip path = %s' % zip_path)
            # now we need
            """*parsed_pid - result of parsing pid
            **problem** canonical_pid - canonicalized with URL prefix
            targets - list of (stitched) targets
            hdr - result of parsing header file
            timestamp - timestamp (FIXME in what format?)
            roi_path - path to ROI file
            outfile - where to write resulting zip file"""
            client.complete(
                pid,
                state='available',
                event='complete',
                message='pretended to create %s' % zip_path)
        except Exception as e:
            logging.warn('ERROR during zip for %s' % pid)
            client.complete(
                pid,
                state='error',
                event='exception',
                message=str(e))
