import requests

from oii.utils import gen_id

from oii.workflow.orm import STATE, NEW_STATE, EVENT, MESSAGE
from oii.workflow.orm import WAITING, RUNNING, AVAILABLE
from oii.workflow.orm import ROLE, ANY
from oii.workflow.orm import HEARTBEAT
from oii.workflow.orm import UPSTREAM

def isok(r):
    return r.status_code < 400

class WorkflowClient(object):
    def __init__(self, base_url='http://localhost:8080'):
        self.base_url = base_url
    def api(self, url):
        return self.base_url + url
    def wakeup(self, pid=None):
        if pid is None:
            return requests.get(self.api('/wakeup'))
        else:
            return requests.get(self.api('/wakeup/%s' % pid))
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
    def heartbeat(self,pid,**d):
        d[EVENT] = HEARTBEAT
        return requests.post(self.api('/update/%s' % pid), data=d)
    def depend(self,pid, upstream, role):
        return requests.post(self.api('/depend/%s' % pid), data={
            UPSTREAM: upstream,
            ROLE: role
        })

class Oneshot(object):
    """used for a single thing that has to be done
    periodically but only have one process at a time doing it
    and don't accumulate a backlog of jobs.
    - initiator calls create, which creates product in
    WAITING state. if that fails, work is already underway
    and initiator returns. if it succeeds, wakes up workers.
    - worker wakes up, calls acquire attempts to update the product from
    WAITING to RUNNING. if that succeeds, it does work and
    calls release. if not, it terminates. if the client fails
    to call release, other workflow ORM clients can force the mutex
    to expire."""
    def __init__(self, client, pid=None):
        self.client = client
        if pid is None:
            pid = get_id()
        self.pid = pid
    def create(self):
        """create mutex and wake up all workers"""
        if isok(self.client.create(self.pid, state=WAITING)):
            self.client.wakeup(self.pid)
    def acquire(self):
        # default state transition is WAITING -> RUNNING
        return isok(self.client.update_if(self.pid))
    def heartbeat(self):
        return self.client.heartbeat(self.pid)
    def release(self):
        # done working, clean slate
        self.client.delete(self.pid)
