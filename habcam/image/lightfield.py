from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re
from oii.workflow.rabbit import Job, JobExit, WIN, FAIL, SKIP
from oii.workflow.workers import ProcessWorker
from oii.config import get_config

class HabcamLightfield(ProcessWorker):
    """messages should be absolute paths to image names.
    expects the following in config:
    queue_name - RabbitMQ queue basename
    amqp_host - RabbitMQ host
    imagestack_exec_path - path to imagestack executable
    in_prefix - prefix regex to strip off of output paths
    out_dir - top-level dir to deposit output"""
    def __init__(self,config):
        super(HabcamLightfield,self).__init__(config)
        script = self.get_script()
        self.imagestack = Process(script)
    def get_script(self):
        return ''
    def get_parameters(self,message):
        img_in = message
        img_out_file = re.sub(self.config.in_prefix,'',re.sub(r'\.tif','.png',img_in)).lstrip('/')
        print 'img_out_file = %s' % img_out_file
        img_out = os.path.join(self.config.out_dir,img_out_file)
        print 'img_out = %s' % img_out
        if os.path.exists(img_out):
            self.log('SKIP already exists: %s %s %s' % (self.config.out_dir, img_in, img_out))
            raise JobExit('Output file already exists: %s' % img_out, SKIP)
        od = os.path.dirname(img_out)
        if not os.path.exists(od):
            os.makedirs(od)
        return dict(img_in=img_in,img_out=img_out)

class HabcamLightfieldNhv(HabcamLightfield):
    """Note that this impl uses NHV's modded version of ImageStack containing wls2 and histoadapt operators"""
    def get_script(self):
        return ' '.join([self.config.imagestack_exec_path,
                         '-load %(img_in)s',
                         '-crop 0 0 1360 1024',
                         '-demosaic 1 0 1',
                         '-colorconvert rgb lab',
                         '-dup',
                         '-downsample',
                         '-wls2 2.5 0.25 100 0.025',
                         '-upsample',
                         '-add',
                         '-histoadapt 0.45 1.25 2 10 4',
                         '-colorconvert lab rgb',
                         '-clamp',
                         '-save %(img_out)s'
                         ])

class HabcamLightfieldJoe(HabcamLightfield):
    def get_script(self):
        return ' '.join([self.config.imagestack_exec_path,
                         '-load %(img_in)s',
                         '-demosaic 1 0 1',
                         '-crop 0 0 1360 1024',
                         '-dup',
                         '-rectfilter %(filter_size)s',
                         '-pull 1 -subtract',
                         '-normalize -scale 2.5 -clamp',
                         '-save %(img_out)s'
                         ])
    def get_parameters(self):
        p = super(HabcamLighfieldJoe,self).get_parameters()
        p['filter_size'] = 501
        return p

def enqueue_from_stdin(hl):
    batch = []
    while True:
        line = sys.stdin.readline()
        if line == '':
            break
        line = line.strip()
        batch = batch + [line]
        if len(batch) > 1000:
            print batch
            hl.enqueue(batch)
            batch = []
    hl.enqueue(batch)

# usage:
# python lightfield.py {config file} {command} {arguments}
# commands:
# q (file1, file2, file3, ... filen)
#   enqueue files for processing
# q -
#   read a list of files to process from stdin
# r
#   requeue failed processing jobs
# w
#   run as a worker
# log
#   show logging messages as they come in
if __name__=='__main__':
    hl = HabcamLightfieldNhv(get_config(sys.argv[1]))
    cmd = sys.argv[2]
    if cmd == 'q':
        if sys.argv[3] == '-':
            enqueue_from_stdin(hl)
        else:
            hl.enqueue(sys.argv[3:])
    elif cmd == 'r':
        hl.retry_failed()
    elif cmd == 'w':
        hl.work()
    elif cmd == 'log':
        hl.consume_log()


