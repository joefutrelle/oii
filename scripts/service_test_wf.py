import time
import sys
from datetime import timedelta

from oii.utils import gen_id

import requests

BASE_URL = 'http://localhost:8080'

def api(url):
    return BASE_URL + url

def do_work():
    d = None
    while True:
        r = requests.get(api('/start_next/acq_wakeup'))
        if r.status_code == 404:
            break
        if d is not None:
            print 'skipping %s' % job_pid
            requests.post(api('/update/%s' % job_pid), data={
                'state': 'available',
                'event': 'skipped'
            })
        d = r.json()
        job_pid = d['pid']
    if d is None:
        print 'nothing to do'
        return False
    print 'completing %s' % job_pid
    requests.post(api('/update/%s' % job_pid), data={
        'state': 'available',
        'event': 'completed'
    })
    return True

print 'creating work'

for n in range(5):
    ping_pid = gen_id()
    job_pid = gen_id()
    print 'pinging: %s <- %s' % (job_pid, ping_pid)
    requests.get(api('/create/%s' % ping_pid))
    requests.post(api('/depend/%s' % job_pid), data={
        'upstream': ping_pid,
        'role': 'acq_wakeup'
    })

print 'starting work'

while do_work():
    print 'looking for more work'

print 'done working'
