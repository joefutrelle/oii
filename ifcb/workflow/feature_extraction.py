import os
import sys
import shutil
import re
import time
import logging

from celery import Celery
from celery.signals import after_setup_task_logger

from oii.ifcb.workflow.deposit_client import Deposit

from oii.resolver import parse_stream
from oii.ifcb.db import IfcbFeed
from oii.utils import gen_id, retry
from oii.config import get_config
from oii.matlab import Matlab
from oii.ifcb import represent
from oii.iopipes import UrlSource, LocalFileSink, drain

MODULE='oii.ifcb.workflow.feature_extraction'

celery = Celery(MODULE)

logger = logging.getLogger(MODULE)

def celery_logging(**kw):
    logger = logging.getLogger(MODULE)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

after_setup_task_logger.connect(celery_logging)

CHECK_EVERY=30

MATLAB_DIRS = [
    'webservice_tools',
    'feature_extraction',
    'feature_extraction/blob_extraction',
    'feature_extraction/batch_features_bins',
    'feature_extraction/biovolume',
    'dipum_toolbox_2.0.1'
]

SKIP='skip'
DIE='die'
WIN='win'
FAIL='fail'

class JobExit(Exception):
    def __init__(self, message, ret):
        self.message = message
        self.ret = ret
    def __str__(self):
        return '%s - %s' % (self.message, self.ret)

def csvname(url):
    return re.sub(r'.*/([^.]+).*',r'\1_fea_v2.csv',url)

def multiblobname(url):
    return re.sub(r'.*/([^.]+).*',r'\1_multiblob_v2.csv',url)

def binzipname(url):
    return re.sub(r'.*/([^.]+).*',r'\1.zip',url)

@retry(IOError, tries=4, delay=1, backoff=2)
def exists(deposit,bin_pid):
    return deposit.exists(bin_pid)

class FeatureExtraction(object):
    def __init__(self, config):
        self.configure(config)
    def configure(self, config):
        self.config = config
        self.config.matlab_path = [os.path.join(self.config.matlab_base, md) for md in MATLAB_DIRS]
        self.deposit = Deposit(self.config.features_deposit, product_type='features')
        self.multiblob_deposit = Deposit(self.config.features_deposit, product_type='multiblob')
        self.resolver = parse_stream(self.config.resolver)
        self.last_check = time.time()
    def complete(self,bin_pid):
        return exists(self.deposit, bin_pid)
    def preflight(self):
        for p in self.config.matlab_path:
            if not os.path.exists(p):
                raise
        if not os.path.exists(self.config.tmp_dir):
            raise
        tempfile = os.path.join(self.config.tmp_dir,gen_id()+'.txt')
        with open(tempfile,'w') as tf:
            tf.write('test')
            tf.flush()
        if not os.path.exists(tempfile):
            raise
        os.remove(tempfile)
        if os.path.exists(tempfile):
            raise
    def log(self,message):
        print message
    def extract_features(self,bin_pid):
        jobid = gen_id()[:5]
        def selflog(line):
            self.log('[%s] %s' % (jobid, line))
        def self_check_log(line,bin_pid):
            selflog(line)
            now = time.time()
            elapsed = now - self.last_check
            self.last_check = now
            if elapsed > CHECK_EVERY:
                if self.complete(bin_pid):
                    msg = 'STOPPING JOB - %s completed by another worker' % bin_pid
                    selflog(msg)
                    raise JobExit(msg, SKIP)
        if self.complete(bin_pid):
            selflog('SKIPPING %s - already completed' % bin_pid)
            return SKIP
        job_dir = os.path.join(self.config.tmp_dir, gen_id())
        zip_dir = os.path.join(self.config.tmp_dir, gen_id())
        bin_zip_path = os.path.join(zip_dir, binzipname(bin_pid))
        try:
            os.makedirs(job_dir)
            selflog('CREATED temporary directory %s for %s' % (job_dir, bin_pid))
        except:
            selflog('WARNING cannot create temporary directory %s for %s' % (job_dir, bin_pid))
        try:
            os.makedirs(zip_dir)
            selflog('CREATED temporary directory %s for %s' % (zip_dir, bin_pid))
        except:
            selflog('WARNING cannot create temporary directory %s for %s' % (zip_dir, bin_pid))
        selflog('LOADING and STITCHING %s' % bin_pid)
        with open(bin_zip_path,'wb') as binzip:
            represent.binpid2zip(bin_pid, binzip, resolver=self.resolver)
        blobzipurl = bin_pid + '_blob.zip'
        blobzipfile = re.sub(r'\.zip','_blob.zip',bin_zip_path)
        selflog('LOADING blob zip from %s -> %s' % (blobzipurl, blobzipfile))
        drain(UrlSource(blobzipurl), LocalFileSink(blobzipfile))
        feature_csv = os.path.join(job_dir, csvname(bin_pid))
        multiblob_csv = os.path.join(job_dir, 'multiblob', multiblobname(bin_pid))
        matlab = Matlab(self.config.matlab_exec_path,self.config.matlab_path,output_callback=lambda l: self_check_log(l, bin_pid))
        namespace = os.path.dirname(bin_zip_path) + '/'
        lid = os.path.basename(bin_zip_path)
        cmd = 'bin_features(\'%s\',\'%s\',\'%s\',\'chatty\')' % (namespace, lid, job_dir + '/')
        selflog('RUNNING %s' % cmd)
        try:
            self.output_check = CHECK_EVERY
            matlab.run(cmd)
            if not os.path.exists(feature_csv):
                msg = 'WARNING bin_features succeeded but no output file found at %s' % feature_csv
                selflog(msg)
                raise JobExit(msg,FAIL)
            if not self.complete(bin_pid): # check to make sure another worker hasn't finished it in the meantime
                selflog('DEPOSITING features csv for %s to deposit service at %s' % (bin_pid, self.config.features_deposit))
                self.deposit.deposit(bin_pid,feature_csv)
                selflog('DEPOSITED features csv for %s ' % bin_pid)
                if os.path.exists(multiblob_csv):
                    selflog('DEPOSITING multiblob csv for %s to deposit service at %s' % (bin_pid, self.config.features_deposit))
                    self.multiblob_deposit.deposit(bin_pid,multiblob_csv)
                    selflog('DEPOSITED multiblob csv for %s ' % bin_pid)
            else:
                selflog('NOT SAVING - features for %s already present at output destination' % bin_pid)
        except KeyboardInterrupt:
            selflog('KeyboardInterrupt, exiting')
            return DIE
        except JobExit:
            pass
        finally:
            try:
                shutil.rmtree(job_dir)
                selflog('DELETED temporary directory %s for %s' % (job_dir, bin_pid))
            except:
                selflog('WARNING cannot remove temporary directory %s for %s' % (job_dir, bin_pid))
            try:
                shutil.rmtree(zip_dir)
                selflog('DELETED temporary directory %s for %s' % (zip_dir, bin_pid))
            except:
                selflog('WARNING cannot remove temporary directory %s for %s' % (zip_dir, bin_pid))
            selflog('DONE - no more actions for %s' % bin_pid)

CONFIG_FILE = './features.conf' # FIXME hardcoded

@celery.task
def extract_features(time_series, bin_pid):
    """config needs matlab_base, matlab_exec_path, tmp_dir, blob_deposit"""
    be = FeatureExtraction(get_config(CONFIG_FILE, time_series))
    be.extract_features(bin_pid)

if __name__=='__main__':
    config_file = sys.argv[1]
    time_series = sys.argv[2]
    bin_pid = sys.argv[3]
    be = FeatureExtraction(get_config(config_file, time_series))
    be.extract_features(bin_pid)
