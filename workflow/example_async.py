import time
import sys
from datetime import timedelta

from oii.utils import gen_id
from oii.workflow.client import WorkflowClient
from oii.workflow.async import async, WAKEUP_TASK
from oii.workflow.orm import STATE, EVENT, MESSAGE, ROLE
from oii.workflow.orm import AVAILABLE, UPSTREAM

import requests

BASE_URL = 'http://localhost:8080'

PING_ROLE='acq_ping_role'

client = WorkflowClient(BASE_URL)

def do_work():
    d = None
    while True:
        # acquire a job
        r = client.start_next(PING_ROLE)
        # no more work, so we either found some or didn't
        if r.status_code == 404:
            break
        # found a job
        if d is not None:
            # so skip the one we were just about to do
            print 'skipping %s' % job_pid
            client.delete_tree(job_pid)
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
    client.update(job_pid, {
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
        client.depend(job_pid, ping_pid, PING_ROLE)

    print 'waking up'
    client.wakeup()

if __name__=='__main__':
    create_work()
