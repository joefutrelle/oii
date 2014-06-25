from __future__ import print_function
import subprocess
import re
from oii.times import iso8601
from traceback import print_exc
import os

def reset_tty():
    pass

def message(msg='WARNING'):
    return ' '.join([iso8601(),str(msg)])

class Matlab:
    def __init__(self,exec_path,matlab_path=['.'],fail_fast=True,output_callback=lambda _: None,log_callback=lambda x: print(x)):
        self.exec_path = exec_path
        self.matlab_path = matlab_path
        self.fail_fast = fail_fast
        self.output_separator = '__BEGIN MATLAB OUTPUT__'
        self.output_callback = output_callback
        self.log_callback = lambda x: log_callback(message(x))
    def run(self,command):
        pathcmds = '; '.join(['path(\'%s\',path)' % d for d in self.matlab_path])
        p = None
        try:
            script = '%s; try, disp(\'%s\'), %s, catch err, disp(err.message), disp(err.stack), disp(err.identifier), exit(1), end, exit(0)' % (pathcmds, self.output_separator, command)
            cmd = [
                self.exec_path,
                '-nodisplay',
                '-r',
                script
                ]
            p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)#,env=env)
            seen_separator = False
            try:
                while p.poll() is None:
                    while True:
                        line = p.stdout.readline()
                        if not line:
                            break
                        line = line.rstrip()
                        if seen_separator:
                            try:
                                self.output_callback(line)
                            except:
                                self.log_callback('Output callback raised exception; killing Matlab process %d' % p.pid)
                                reset_tty()
                                p.kill()
                                raise
                        elif not seen_separator and line == self.output_separator:
                            seen_separator = True
            except:
                self.log_callback('Matlab exited')
            if p.returncode is not None and p.returncode != 0 and self.fail_fast:
                self.log_callback('Matlab return code is %d' % p.returncode)
                raise RuntimeError('Nonzero return code (%d) from Matlab process %d' % (p.pid, p.returncode))
        except KeyboardInterrupt:
            self.log_callback('Keyboard interrupt; killing Matlab process %d' % p.pid)
            reset_tty()
            p.kill()
            raise
        except:
            print_exc()
            reset_tty()
            try:
                p.kill()
            except OSError:
                print('did not kill, no such process')
            if self.fail_fast:
                raise
