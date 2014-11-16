import requests

from oii.workflow.orm import STATE, NEW_STATE, EVENT, MESSAGE
from oii.workflow.orm import WAITING, AVAILABLE, ROLE, ANY, HEARTBEAT, UPSTREAM, RUNNING

import logging

class WorkflowClient(object):
    def __init__(self, base_url='http://localhost:8080'):
        self.base_url = base_url
    def api(self, url):
        return self.base_url + url
    def wakeup(self):
        return requests.get(self.api('/wakeup'))
    def start_next(self,roles):
        if isinstance(roles,basestring):
            roles = [roles]
        return requests.get(self.api('/start_next/%s' % '/'.join(roles)))
    def create(self,pid,**d):
        return requests.post(self.api('/create/%s' % pid), data=d)
    def update_if(self,pid, **d):
        """d must contain STATE and NEW_STATE,
        d can also contain EVENT, MESSAGE"""
        return requests.post(self.api('/update_if/%s' % pid), data=d)
    def delete(self,pid):
        return requests.delete(self.api('/delete/%s' % pid))
    def delete_tree(self,pid):
        return requests.delete(self.api('/delete_tree/%s' % pid))
    def update(self,pid, **d):
        """d can contain STATE, EVENT, MESSAGE"""
        return requests.post(self.api('/update/%s' % pid), data=d)
    def depend(self,pid, upstream, role):
        return requests.post(self.api('/depend/%s' % pid), data={
            UPSTREAM: upstream,
            ROLE: role
        })
