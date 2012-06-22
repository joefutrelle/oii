from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re
from oii.workflow.rabbit import Job, WIN
from oii.config import get_config

class HabcamLightfield(Job):
    """messages should be absolute paths to image names.
    expects the following in config:
    queue_name - RabbitMQ queue basename
    imagestack_exec_path - path to imagestack executable
    out_dir - top-level dir to deposit output"""
    def __init__(self,config):
        super(HabcamLightfield,self).__init__(config.queue_name, config.amqp_host)
        self.config = config
        script = ' '.join([self.config.imagestack_exec_path,
            '-load %(img_in)s',
            '-demosaic 1 0 1',
            '-crop 0 0 1360 1024',
            '-dup',
            '-rectfilter %(filter_size)s',
            '-pull 1 -subtract',
            '-normalize -scale 2.5 -clamp',
            '-save %(img_out)s'
            ])
        self.imagestack = Process(script)
    def run_callback(self,message):
        try:
            img_in = message
            img_out = os.path.join(self.config.out_dir,img_in)
            if os.path.exists(img_out):
                return SKIP
            od = os.path.dirname(img_out)
            if not os.path.exists(od):
                os.makedirs(od)
            for msg in self.imagestack.run(dict(img_in=img_in,filter_size=501,img_out=img_out)):
                self.log(msg['message'])
            return WIN
        except:
            return FAIL

if __name__=='__main__':
    hl = HabcamLightfield(get_config(sys.argv[1]))
    cmd = sys.argv[2]
    if cmd == 'q':
        hl.enqueue(sys.argv[3:])
    elif cmd == 'w':
        hl.work()


