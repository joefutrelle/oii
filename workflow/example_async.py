import time
import sys
from datetime import timedelta

from oii.utils import gen_id
from oii.workflow.async import async, WAKEUP_TASK
from oii.workflow.orm import STATE, EVENT, MESSAGE, ROLE
from oii.workflow.orm import AVAILABLE, UPSTREAM

import requests

BASE_URL = 'http://localhost:8080'

PING_ROLE='acq_ping_role'

def api(url):
    return BASE_URL + url

def start_next(role):
    return requests.get(api('/start_next/%s' % role))

def delete_tree(pid):
    requests.delete(api('/delete_tree/%s' % pid))

def update(pid, d):
    requests.post(api('/update/%s' % pid), data=d)

def depend(pid, upstream, role):
    requests.post(api('/depend/%s' % pid), data={
        UPSTREAM: upstream,
        ROLE: role
    })

def do_work():
    d = None
    while True:
        # acquire a job
        r = start_next(PING_ROLE)
        # no more work, so we either found some or didn't
        if r.status_code == 404:
            break
        # found a job
        if d is not None:
            # so skip the one we were just about to do
            print 'skipping %s' % job_pid
            delete_tree(job_pid)
        # remember this job for next iteration
        d = r.json()
        job_pid = d['pid']
    # turns out we never found a job
    if d is None:
        print 'nothing to do'
        return False
    # we found a job, so say we did it
    print 'completing %s' % job_pid
    # update product state
    update(job_pid, {
        STATE: AVAILABLE,
        EVENT: 'completed',
        MESSAGE: 'said we did it'
    })
    return True

@async.task(name=WAKEUP_TASK)
def do_a_buncha_work():
    print 'starting work'

    while do_work():
        print 'looking for more work'

    print 'done working'

def create_work():
    print 'creating work'

    for n in range(5):
        ping_pid = gen_id()
        job_pid = gen_id()
        print 'pinging: %s <- %s' % (job_pid, ping_pid)
        depend(job_pid, ping_pid, PING_ROLE)

    print 'waking up'
    requests.get(api('/wakeup'))

if __name__=='__main__':
    create_work()
