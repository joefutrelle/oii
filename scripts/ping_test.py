import sys
import traceback
import random
import time
from multiprocessing import Pool
from oii.workflow.orm import STATE, NEW_STATE, AVAILABLE, RUNNING, WAITING
from oii.workflow.client import WorkflowClient

import httplib as http

client = WorkflowClient()

PING_PID = 'ping_test'

def random_sleep():
    time.sleep(random.random())

def worker(n):
    # race to create the ping
    if random.random() < 0.2:
        r = create_ping()
        if r.status_code==http.CREATED:
            print 'worker %d created the ping' % n
            return
        else:
            print 'worker %d got 409, ping already exists' % n
    random_sleep()
    r = client.update_if(PING_PID)
    if r.status_code==http.OK:
        print '>>>>> worker %d' % n
        for i in range(2):
            random_sleep()
            print 'worker %d did some work' % n
        r = client.update(PING_PID, state=WAITING)
        if r.status_code != http.OK:
            print 'worker %d FAILED to release ping, dying' % n
        print '<<<<< worker %d' % n
    else:
        print '(worker %d skipped)' % n

def do_work():
    N=10
    pool = Pool(3)
    for n in range(N):
        pool.apply_async(worker,[n],{})
    pool.close()
    pool.join()

def create_ping():
    return client.create(PING_PID, state=WAITING)

def delete_ping():
    client.delete(PING_PID)

def doit():
    do_work()
    delete_ping()

if __name__=='__main__':
    doit()
    
