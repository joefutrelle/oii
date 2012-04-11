import subprocess
import re
from oii.times import iso8601
from traceback import print_exc

def reset_tty():
    subprocess.call(['stty','echo'])

def message(msg='WARNING'):
    return ' '.join(iso8601(),msg)

class Matlab:
    def __init__(self,exec_path,matlab_path=['.'],fail_fast=True,output_callback=lambda _: None):
        self.exec_path = exec_path
        self.matlab_path = matlab_path
        self.fail_fast = fail_fast
        self.output_separator = '__BEGIN MATLAB OUTPUT__'
        self.output_callback = output_callback
    def run(self,command):
        env = dict(MATLABPATH=':'.join(self.matlab_path))
        p = None
        try:
            script = 'try, disp(\'%s\'), %s, catch err, disp(err.identifier), exit(1), end, exit(0)' % (self.output_separator, command)
            cmd = [
                self.exec_path,
                '-nodisplay',
                '-r',
                script
                ]
            p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
            seen_separator = False
            while p.poll() is None:
                while True:
                    line = p.stdout.readline()
                    if not line:
                        break
                    line = line.rstrip()
                    if seen_separator:
                        self.output_callback(line)
                    elif not seen_separator and line == self.output_separator:
                        seen_separator = True
            if p.returncode != 0 and self.fail_fast:
                print 'return code is %d' % p.returncode
                raise RuntimeError('nonzero return code from subprocess: %d' % p.returncode)
            reset_tty()
        except KeyboardInterrupt:
            print 'killing matlab process %d' % p.pid
            p.kill()
            reset_tty()
            raise
        except:
            reset_tty()
            print_exc()
            if self.fail_fast:
                raise
