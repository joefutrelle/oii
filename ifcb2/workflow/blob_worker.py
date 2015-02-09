import os
import re
import logging
 
import requests
 
from oii.utils import safe_tempdir
from oii.matlab import Matlab

from oii.workflow import FOREVER, AVAILABLE, COMPLETED, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE
from oii.ifcb2.workflow import BINZIP2BLOBS
from oii.ifcb2.identifiers import parse_pid, PID, LID 

### FIXME config this right
client = WorkflowClient('http://128.128.14.19:9270')

# configure MATLAB
MATLAB_EXEC_PATH='/usr/local/MATLAB/R2014b/bin/matlab'
MATLAB_BASE='/home/ubuntu/dev/trunk'
MATLAB_DIRS=[
'feature_extraction',
'feature_extraction/blob_extraction',
'webservice_tools',
'dipum_toolbox_2.0.1'
]
MATLAB_PATH = [os.path.join(MATLAB_BASE, md) for md in MATLAB_DIRS] 

def blob_zip_name(bin_pid):
    return re.sub(r'.*/([^.]+).*',r'\1_blobs_v2.zip',bin_pid)

def extract_blobs(pid,job):
    logging.warn('BLOBS computing blobs for %s' % pid)
    parsed_pid = parse_pid(pid)
    bin_lid = parsed_pid[LID]
    bin_pid = ''.join([parsed_pid[NAMESPACE], parsed_pid[LID]]) 
    binzip_url = ''.join([bin_pid,'_binzip.zip'])
    binzip_file = os.path.basename(binzip_url)
    with safe_tempdir() as binzip_dir:
        # first, copy the zipfile to a temp dir
        binzip_path = os.path.join(binzip_dir, '%s.zip' % bin_lid)
        logging.warn('BLOBS downloading %s to %s' % (binzip_url, binzip_path))
        r = requests.get(binzip_url)
        with open(binzip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                f.write(chunk)
                f.flush()
        # now run bin_blobs
        with safe_tempdir() as job_dir:
            # configure matlab
            def log_callback(msg):
                logging.warn('BLOBS %s' % msg)
                client.heartbeat(pid,message=msg)
            matlab = Matlab(MATLAB_EXEC_PATH, MATLAB_PATH, output_callback=log_callback)
            # run command
            blobs_file = os.path.join(job_dir, blob_zip_name(bin_pid))
            cmd = 'bin_blobs(\'%s\',\'%s\',\'%s\')' % (bin_pid, binzip_path, job_dir)
            logging.warn('BLOBS running %s' % cmd)
            matlab.run(cmd)
            logging.warn('BLOBS checking for %s' % blobs_file)
            if not os.path.exists(blobs_file):
                raise Exception('missing output file')
            deposit_url = '%s_blobs.zip' % bin_pid 
            logging.warn('BLOBS depositing %s' % blobs_file)
            with open(blobs_file,'rb') as bi:
                bytez = bi.read() # read and pass bytes as data for 12.04 version of requests
                requests.put(deposit_url, data=bytez)
            logging.warn('BLOBS deposited %s' % blobs_file)
    logging.warn('BLOBS completed %s' % bin_pid)
    client.wakeup()

@wakeup_task
def blob_wakeup(wakeup_key):
    client.do_all_work([BINZIP2BLOBS],extract_blobs,'blob zip deposited')
