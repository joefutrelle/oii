from oii.times import iso8601ms
from oii.utils import gen_id
from subprocess import Popen, PIPE

def timestamped_output_of(cmd,stdout=True,jobid=None):
    issued = iso8601ms()
    if jobid is None:
        jobid = gen_id()
    def log_struct(message):
        return {
            'command': cmd,
            'issued': issued,
            'jobid': jobid,
            'message': message,
            'timestamp': iso8601ms()
            }
    yield log_struct('executing shell command %s, jobid %s' % (cmd,jobid))
    if stdout:
        p = Popen(cmd, shell=True, stdout=PIPE)
    else:
        p = Popen(cmd, shell=True, stderr=PIPE)
    while True:
        if stdout:
            line = p.stdout.readline()
        else:
            line = p.stderr.readline()
        if not line:
            p.wait()
            if p.returncode != 0:
                message = 'process exited abnormally with exit code %d: %s' % (p.returncode, cmd)
                yield log_struct(message)
                raise RuntimeError(message)
            yield log_struct('process closed output stream: '+cmd)
            return
        yield log_struct(line.rstrip('\n'))

class Process(object):
    def __init__(self,command):
        self.command = command
    def run(self,params={}):
        for log_msg in timestamped_output_of(self.command % params):
            yield log_msg
