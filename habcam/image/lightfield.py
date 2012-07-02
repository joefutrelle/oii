from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re
from oii.workflow.rabbit import Job, WIN, FAIL, SKIP
from oii.config import get_config

class HabcamLightfield(Job):
    """messages should be absolute paths to image names.
    expects the following in config:
    queue_name - RabbitMQ queue basename
    amqp_host - RabbitMQ host
    imagestack_exec_path - path to imagestack executable
    out_dir - top-level dir to deposit output"""
    def __init__(self,config):
        super(HabcamLightfield,self).__init__(config.queue_name, config.amqp_host)
        self.config = config
        script = self.get_script()
        self.imagestack = Process(script)
    def get_script(self):
        return ''
    def get_parameters(self):
        return {}
    def run_callback(self,message):
        try:
            img_in = message
            img_out = os.path.join(self.config.out_dir,re.sub(r'\.tif','.png',img_in.lstrip('/')))
            if os.path.exists(img_out):
                print 'already exists: %s %s %s' % (self.config.out_dir, img_in, img_out)
                return SKIP
            od = os.path.dirname(img_out)
            if not os.path.exists(od):
                os.makedirs(od)
            params = dict(dict(img_in=img_in,img_out=img_out).items() + self.get_parameters().items())
            for msg in self.imagestack.run(params):
                self.log(msg['message'])
            return WIN
        except:
            raise

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
    def get_parameters(self):
        return {}

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
        return dict(filter_size=501)

if __name__=='__main__':
    hl = HabcamLightfieldNhv(get_config(sys.argv[1]))
    cmd = sys.argv[2]
    if cmd == 'q':
        hl.enqueue(sys.argv[3:])
    elif cmd == 'r':
        hl.retry_failed()
    elif cmd == 'w':
        hl.work()
    elif cmd == 'log':
        hl.consume_log()


