import os
import sys
import shutil
import re
import time

from oii.ifcb.workflow.blob_deposit import BlobDeposit

from oii.utils import gen_id
from oii.config import get_config
from oii.matlab import Matlab

CHECK_EVERY=200

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

class BlobExtraction(object):
    def __init__(self, config):
        self.configure(config)
    def configure(self, config):
        self.config = config
        self.config.matlab_path = [os.path.join(self.config.matlab_base, md) for md in MATLAB_DIRS]
        self.deposit = BlobDeposit(self.config.blob_deposit)
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
            self.log('%s %s' % (jobid, line))
        def self_check_log(line,bin_pid):
            selflog(line)
            self.output_check -= 1
            if self.output_check <= 0:
                if self.exists(bin_pid):
                    selflog('STOPPING JOB - %s completed by another worker' % bin_pid)
                    return SKIP
                self.output_check = CHECK_EVERY
        if self.exists(bin_pid):
            selflog('SKIPPING %s - already completed' % bin_pid)
            return SKIP
        job_dir = os.path.join(self.config.tmp_dir, gen_id())
        try:
            os.makedirs(job_dir)
            selflog('CREATED temporary directory %s' % job_dir)
        except:
            selflog('WARNING cannot create temporary directory %s' % job_dir)
        tmp_file = os.path.join(job_dir, zipname(bin_pid))
        matlab = Matlab(self.config.matlab_exec_path,self.config.matlab_path,output_callback=lambda l: self_check_log(l, bin_pid))
        cmd = 'bin_blobs(\'%s\',\'%s\')' % (bin_pid, job_dir)
        try:
            self.output_check = CHECK_EVERY
            matlab.run(cmd)
            if not os.path.exists(tmp_file):
                selflog('WARNING bin_blobs succeeded but no output file found at %s' % tmp_file)
            elif not self.exists(bin_pid): # check to make sure another worker hasn't finished it in the meantime
                selflog('DEPOSITING blob zip for %s to deposit service' % bin_pid)
                self.deposit.deposit(bin_pid,tmp_file)
            else:
                selflog('NOT SAVING - blobs for %s already present at output destination' % bin_pid)
        except KeyboardInterrupt:
            selflog('KeyboardInterrupt, exiting')
            return DIE
        finally:
            try:
                shutil.rmtree(job_dir)
            except:
                selflog('WARNING cannot remove temporary directory %s' % job_dir)


if __name__=='__main__':
    bin_pid = sys.argv[1]
    be = BlobExtraction(get_config('./blob.conf','mvco'))
    be.extract_blobs(bin_pid)
