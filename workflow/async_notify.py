from celery import Celery

APP_NAME='oii.workflow.async'
WAKEUP_TASK=APP_NAME+'.wakeup'

"""
define a wakeup task in your worker code like this:

@celery.task(WAKEUP_TASK)
def my_method():
    pass
"""

celery = Celery(APP_NAME)

def async_config(config_module='oii.workflow.async_config'):
    celery.config_from_object(config_module)

def async_wakeup():
    """asynchronously wake up all workers"""
    celery.send_task(WAKEUP_TASK)

if __name__=='__main__':
    async_config()
    async_wakeup()
