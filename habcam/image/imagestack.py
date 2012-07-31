from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re
from oii.workflow.rabbit import Job, JobExit, WIN, FAIL, SKIP
from oii.workflow.workers import ProcessWorker
from oii.config import get_config

class ImageStackWorker(ProcessWorker):
    """messages should be absolute paths to image names.
    expects the following in config:
    queue_name - RabbitMQ queue basename
    amqp_host - RabbitMQ host
    imagestack_exec_path - path to imagestack executable
    in_prefix - prefix regex to strip off of output paths
    out_dir - top-level dir to deposit output"""
    def __init__(self,config):
        super(ImageStackWorker,self).__init__(config)
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

def cli(job,argv):
    cmd = sys.argv[2]
    if cmd == 'q':
        if sys.argv[3] == '-':
            enqueue_from_stdin(job)
        else:
            job.enqueue(sys.argv[3:])
    elif cmd == 'r':
        job.retry_failed()
    elif cmd == 'w':
        job.work()
    elif cmd == 'log':
        job.consume_log()

