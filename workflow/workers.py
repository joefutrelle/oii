from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re
from oii.workflow.rabbit import Job, WIN, FAIL, SKIP
from oii.config import get_config

class ProcessWorker(Job):
    """messages can be anything.
    queue_name - RabbitMQ queue basename
    amqp_host - RabbitMQ host"""
    def __init__(self,config):
        super(ProcessWorker,self).__init__(config.queue_name, config.amqp_host)
        self.config = config
        self.process = Process(self.get_script())
    def get_script(self):
        return ''
    def get_parameters(self,message):
        """Raise JobExit if the message is sufficient to determine an exit status
        (e.g., the job has already been completed by another worker). All validation
        and provisioning (e.g., creating output directories) must take place at this stage"""
        return {}
    def win_callback(self,params):
        return WIN
    def fail_callback(self,params):
        return FAIL
    def run_callback(self,message):
        try:
            params = self.get_parameters(message)
            try:
                for msg in self.process.run(params):
                    self.log(msg['message'])
                return self.win_callback(params)
            except RuntimeError:
                return self.fail_callback(params)
        except:
            raise

