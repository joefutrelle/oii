import time
import sys
from datetime import timedelta

from oii.utils import gen_id
from oii.workflow.client import WorkflowClient, isok
from oii.workflow.async import async, wakeup_task, WAKEUP_TASK
from oii.workflow.orm import PID, STATE, EVENT, MESSAGE, ROLE
from oii.workflow.orm import AVAILABLE, UPSTREAM

import requests

BASE_URL = 'http://localhost:8080'

PING_ROLE='acq_ping_role'

WAKEUP_KEY='oii.workflow.example_async.singleton'

client = WorkflowClient(BASE_URL)

def do_work():
    def acquire_jobs():
        while True:
            # acquire a job
            r = client.start_next(PING_ROLE)
            if isok(r):
                job = r.json()
                yield job[PID]
            else:
                return
    jobs = list(acquire_jobs())
    if not jobs:
        print 'DONE no more work'
        return False
    # delete all but one job
    for job in jobs[:-1]:
        print 'WAITING -> (delete) %s' % job
        client.delete_tree(job)
    job = jobs[-1]
    # we found a job, so say we did it
    print 'WAITING -> RUNNING %s' % job
    # update product state
    client.update(job, state=AVAILABLE,
                  event='work',
                  message='said we did it')
    print 'RUNNING -> AVAILABLE %s' % job
    return True

#@async.task(name=WAKEUP_TASK)
@wakeup_task
def do_a_buncha_work(payload):
    if payload != WAKEUP_KEY:
        print 'NOT WAKING UP for %s' % payload
        return

    print 'AWAKE'

    while do_work():
        print 'NEXT looking for more work'

    print 'DONE'

def create_work():
    print 'creating work'

    for n in range(5):
        ping_pid = gen_id()
        job_pid = gen_id()
        print 'pinging: %s <- %s' % (job_pid, ping_pid)
        assert isok(client.depend(job_pid, ping_pid, PING_ROLE))

    print 'waking up'
    assert isok(client.wakeup(WAKEUP_KEY))

if __name__=='__main__':
    create_work()
