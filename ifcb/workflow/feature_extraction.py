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
from oii.utils import gen_id
from oii.config import get_config
from oii.matlab import Matlab

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

class FeatureExtraction(object):
    def __init__(self, config):
        self.configure(config)
    def configure(self, config):
        self.config = config
        self.config.matlab_path = [os.path.join(self.config.matlab_base, md) for md in MATLAB_DIRS]
        self.deposit = Deposit(self.config.features_deposit, product_type='features')
        self.last_check = time.time()
    def complete(self,bin_pid):
        return self.deposit.exists(bin_pid)
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
        try:
            os.makedirs(job_dir)
            selflog('CREATED temporary directory %s for %s' % (job_dir, bin_pid))
        except:
            selflog('WARNING cannot create temporary directory %s for %s' % (job_dir, bin_pid))
        tmp_file = os.path.join(job_dir, csvname(bin_pid))
        matlab = Matlab(self.config.matlab_exec_path,self.config.matlab_path,output_callback=lambda l: self_check_log(l, bin_pid))
        namespace = os.path.dirname(bin_pid) + '/'
        lid = os.path.basename(bin_pid) + '.zip'
        cmd = 'bin_features(\'%s\',\'%s\',\'%s\')' % (namespace, lid, job_dir + '/')
        selflog('RUNNING %s' % cmd)
        try:
            self.output_check = CHECK_EVERY
            matlab.run(cmd)
            if not os.path.exists(tmp_file):
                selflog('WARNING bin_features succeeded but no output file found at %s' % tmp_file)
            elif not self.complete(bin_pid): # check to make sure another worker hasn't finished it in the meantime
                selflog('DEPOSITING features zip for %s to deposit service at %s' % (bin_pid, self.config.features_deposit))
                self.deposit.deposit(bin_pid,tmp_file)
                selflog('DEPOSITED features zip for %s ' % bin_pid)
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
            selflog('DONE - no more actions for %s' % bin_pid)

CONFIG_FILE = './features.conf' # FIXME hardcoded

@celery.task
def extract_features(time_series, bin_pid):
    """config needs matlab_base, matlab_exec_path, tmp_dir, blob_deposit"""
    be = FeatureExtraction(get_config(CONFIG_FILE, time_series))
    be.extract_features(bin_pid)
