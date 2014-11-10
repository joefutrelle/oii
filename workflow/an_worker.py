from celery import Celery

from oii.workflow.async_notify import APP_NAME, WAKEUP_TASK

celery = Celery(APP_NAME)

@celery.task(name=WAKEUP_TASK)
def wakeup():
    print 'worker 1 woke up'

# run worker like this
# default config demonstrated in oii.workflow.async_config
# any config needs to map the wakeup task to a broadcast queue
#
# celery --config=oii.workflow.async_config -A oii.workflow.an_worker worker -n [unique name] [params]
#
# params include -c n for n threads
# and queueing params
