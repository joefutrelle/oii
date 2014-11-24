import time
import sys
from datetime import timedelta

from oii.utils import gen_id
from oii.workflow.async import async, WAKEUP_TASK

import requests

BASE_URL = 'http://localhost:8080'

PING_ROLE='acq_ping_role'

def api(url):
    return BASE_URL + url

def do_work():
    d = None
    while True:
        # acquire a job
        r = requests.get(api('/start_next/%s' % PING_ROLE))
        # no more work, so we either found some or didn't
        if r.status_code == 404:
            break
        # found a job
        if d is not None:
            # so skip the one we were just about to do
            print 'skipping %s' % job_pid
            requests.delete(api('/delete_tree/%s' % job_pid))
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
    requests.post(api('/update/%s' % job_pid), data={
        'state': 'available',
        'event': 'completed',
        'message': 'acquisition done'
    })
    requests.get(api('/wakeup'))
    return True

print 'creating work'

for n in range(5):
    ping_pid = gen_id()
    job_pid = gen_id()
    print 'pinging: %s <- %s' % (job_pid, ping_pid)
    requests.post(api('/depend/%s' % job_pid), data={
        'upstream': ping_pid,
        'role': PING_ROLE
    })

@async.task(name=WAKEUP_TASK)
def do_a_buncha_work():
    print 'starting work'

    while do_work():
        print 'looking for more work'

    print 'done working'
