import os
import re
import logging

import requests

from oii.utils import safe_tempdir
from oii.ioutils import download, upload, exists
from oii.matlab import Matlab

from oii.workflow import FOREVER, AVAILABLE, COMPLETED, ERROR
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, wakeup_task

from oii.ifcb2 import PID, LID, TS_LABEL, NAMESPACE
from oii.ifcb2.workflow import BLOBS2FEATURES
from oii.ifcb2.identifiers import parse_pid
from oii.rbac.utils import secure_upload

from worker_config import WORKFLOW_URL, MATLAB_BASE, MATLAB_EXEC_PATH, API_KEY

client = WorkflowClient(WORKFLOW_URL)

MATLAB_DIRS = [
'webservice_tools',
'feature_extraction',
'feature_extraction/blob_extraction',
'feature_extraction/batch_features_bins',
'feature_extraction/biovolume',
'dipum_toolbox_2.0.1'
]
MATLAB_PATH = [os.path.join(MATLAB_BASE, md) for md in MATLAB_DIRS]

def csvname(url):
    return re.sub(r'.*/([^.]+).*',r'\1_fea_v2.csv',url)

def multiblobname(url):
    return re.sub(r'.*/([^.]+).*',r'\1_multiblob_v2.csv',url)

def binzipname(url):
    return re.sub(r'.*/([^.]+).*',r'\1.zip',url)

def extract_features(pid,job):
    def log_callback(msg):
        logging.warn('FEATURES %s' % msg)
        client.heartbeat(pid,message=msg)
    parsed_pid = parse_pid(pid)
    bin_lid = parsed_pid[LID]
    bin_pid = ''.join([parsed_pid[NAMESPACE], parsed_pid[LID]]) 
    binzip_url = ''.join([bin_pid,'_binzip.zip'])
    blob_url = ''.join([bin_pid,'_blob.zip'])
    features_url = ''.join([bin_pid,'_features.csv'])
    multiblob_url = ''.join([bin_pid,'_multiblob.csv'])
    if exists(features_url):
        log_callback('skipping %s - features exist' % pid)
        return
    log_callback('computing features for %s' % pid)
    with safe_tempdir() as binzip_dir:
        # download bin zip
        binzip_path = os.path.join(binzip_dir, '%s.zip' % bin_lid)
        log_callback('downloading %s to %s' % (binzip_url, binzip_path))
        download(binzip_url, binzip_path)
        # download blob zip
        blob_path = os.path.join(binzip_dir, '%s_blob.zip' % bin_lid)
        log_callback('downloading %s to %s' % (blob_url, blob_path))
        download(blob_url, blob_path)
        # compute features
        with safe_tempdir() as job_dir:
            # output of matlab job
            feature_csv = os.path.join(job_dir, csvname(bin_pid))
            multiblob_csv = os.path.join(job_dir, 'multiblob', multiblobname(bin_pid))
            # params for matlab job
            namespace = os.path.dirname(binzip_path) + '/'
            lid = os.path.basename(binzip_path)
            matlab = Matlab(MATLAB_EXEC_PATH, MATLAB_PATH, output_callback=log_callback)
            cmd = 'bin_features(\'%s\',\'%s\',\'%s\',\'chatty\')' % (namespace, lid, job_dir + '/')
            log_callback('running %s' % cmd)
            matlab.run(cmd)
            log_callback('matlab exited')
            if os.path.exists(feature_csv):
                log_callback('features found at %s' % feature_csv)
            else:
                raise Exception('no features found')
            log_callback('uploading %s' % features_url)
            secure_upload(feature_csv, features_url, API_KEY)
            if os.path.exists(multiblob_csv):
                log_callback('multiblob found at %s' % multiblob_csv)
                log_callback('uploading %s' % multiblob_url)
                upload(multiblob_csv, multiblob_url)
                log_callback('complete')
            client.wakeup()

@wakeup_task
def features_wakeup(wakeup_key):
    client.do_all_work(
        roles=[BLOBS2FEATURES],
        callback=extract_features,
        ttl=310,
        message='features/multiblob CSVs deposited')
