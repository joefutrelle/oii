from celery import Celery

ASYNC='oii.workflow.async'
WAKEUP_TASK=ASYNC+'.wakeup'

"""
define a wakeup task in your worker code like this:

from oii.workflow.async import async, WAKEUP_TASK

@async.task(name=WAKEUP_TASK)
def my_function():
    pass

the function can also accept a single argument which is an arbitrary payload
although said payload must be serializable

default config is in oii.workflow.async_config

any config needs to map the async_wakeup task to a broadcast queue
like this:

from kombu.common import Broadcast

from oii.workflow.async import WAKEUP_TASK

WAKEUP_QUEUE='async_wakeup'

CELERY_QUEUES = (Broadcast(WAKEUP_QUEUE),)
CELERY_ROUTES = { WAKEUP_TASK: { 'queue': WAKEUP_QUEUE } }

(in above, does not matter what 'wakeup queue' is)

run a worker like this

celery --config=oii.workflow.async_config -A my.worker.module worker -n [unique name] [params]

params include -c n for n threads
"""

async = Celery(ASYNC)

def async_config(config_module='oii.workflow.async_config'):
    """use to configure client applications from a module,
    see configuration notes above"""
    async.config_from_object(config_module)

def async_wakeup(payload=None):
    """asynchronously wake up all workers. must be configged"""
    if payload is None:
        async.send_task(WAKEUP_TASK)
    else:
        async.send_task(WAKEUP_TASK, [payload])

# decorator for async.task(name=WAKEUP_TASK)
def wakeup_task(func):
    @async.task(name=WAKEUP_TASK)
    def func_wrapper(*a,**kw):
        try: # try calling with key
            func(*a,**kw)
        except TypeError:
            try:
                func(None,**kw)
            except TypeError:
                func()
    return func_wrapper

if __name__=='__main__':
    # configure client
    async_config()
    # wake up all workers
    async_wakeup()
