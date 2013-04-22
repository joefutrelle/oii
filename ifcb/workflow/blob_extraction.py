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
from oii.ifcb import represent

MODULE='oii.ifcb.workflow.blob_extraction'

celery = Celery(MODULE)

logger = logging.getLogger(MODULE)

def celery_logging(**kw):
    logger = logging.getLogger(MODULE)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

after_setup_task_logger.connect(celery_logging)

CHECK_EVERY=30

MATLAB_DIRS=[
'feature_extraction',
'feature_extraction/blob_extraction',
'webservice_tools',
'dipum_toolbox_2.0.1'
]

SKIP='skip'
DIE='die'
WIN='win'
FAIL='fail'

def zipname(url):
    return re.sub(r'.*/([^.]+).*',r'\1_blobs_v2.zip',url)

def binzipname(url):
    return re.sub(r'.*/([^.]+).*',r'\1.zip',url)

class JobExit(Exception):
    def __init__(self, message, ret):
        self.message = message
        self.ret = ret
    def __str__(self):
        return '%s - %s' % (self.message, self.ret)

class BlobExtraction(object):
    def __init__(self, config):
        self.configure(config)
    def configure(self, config):
        self.config = config
        self.config.matlab_path = [os.path.join(self.config.matlab_base, md) for md in MATLAB_DIRS]
        self.deposit = Deposit(self.config.blob_deposit)
        self.resolver = parse_stream(self.config.resolver)
        self.last_check = time.time()
    def exists(self,bin_pid):
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
    def extract_blobs(self,bin_pid):
        jobid = gen_id()[:5]
        def selflog(line):
            self.log('[%s] %s' % (jobid, line))
        def self_check_log(line,bin_pid):
            selflog(line)
            now = time.time()
            elapsed = now - self.last_check
            self.last_check = now
            if elapsed > CHECK_EVERY:
                if self.exists(bin_pid):
                    msg = 'STOPPING JOB - %s completed by another worker' % bin_pid
                    selflog(msg)
                    raise JobExit(msg, SKIP)
        if self.exists(bin_pid):
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
        tmp_file = os.path.join(job_dir, zipname(bin_pid))
        matlab = Matlab(self.config.matlab_exec_path,self.config.matlab_path,output_callback=lambda l: self_check_log(l, bin_pid))
        cmd = 'bin_blobs(\'%s\',\'%s\',\'%s\')' % (bin_pid, bin_zip_path, job_dir)
        try:
            self.output_check = CHECK_EVERY
            matlab.run(cmd)
            if not os.path.exists(tmp_file):
                selflog('WARNING bin_blobs succeeded but no output file found at %s' % tmp_file)
            elif not self.exists(bin_pid): # check to make sure another worker hasn't finished it in the meantime
                selflog('DEPOSITING blob zip for %s to deposit service at %s' % (bin_pid, self.config.blob_deposit))
                self.deposit.deposit(bin_pid,tmp_file)
                selflog('DEPOSITED blob zip for %s ' % bin_pid)
            else:
                selflog('NOT SAVING - blobs for %s already present at output destination' % bin_pid)
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

CONFIG_FILE = './blob.conf' # FIXME hardcoded

@celery.task
def extract_blobs(time_series, bin_pid):
    """config needs matlab_base, matlab_exec_path, tmp_dir, blob_deposit"""
    be = BlobExtraction(get_config(CONFIG_FILE, time_series))
    be.extract_blobs(bin_pid)

if __name__=='__main__':
    time_series = sys.argv[1]
    bin_lid = sys.argv[2]
    extract_blobs(time_series, bin_lid)
