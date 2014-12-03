import sys
import traceback
import random
import time
from multiprocessing import Pool
from oii.workflow.orm import STATE, NEW_STATE, AVAILABLE, RUNNING, WAITING
from oii.workflow.client import WorkflowClient, Mutex, Busy

import httplib as http

MUTEX_PID = 'my_mutex'

def random_sleep():
    time.sleep(random.random())

def worker(n):
    random_sleep()
    try:
        mutex = Mutex(MUTEX_PID, ttl=30)
        # first attempt to expire any lingering products
        mutex.expire()
        with mutex:
            print 'START %d {' % n
            for i in range(2):
                random_sleep()
                mutex.heartbeat(MUTEX_PID)
                print '  work(%d)' % n
        print '}'
    except Busy:
        print '  skip(%d)' % n
    except:
        traceback.print_exc(file=sys.stdout)

def do_work():
    N=15
    pool = Pool(5)
    for n in range(N):
        pool.apply_async(worker,[n],{})
    pool.close()
    pool.join()

def doit():
    do_work()
    #WorkflowClient().delete(MUTEX_PID)

if __name__=='__main__':
    doit()
    
