from kombu.common import Broadcast

from oii.workflow.async_notify import WAKEUP_TASK

#CELERY_IMPORTS = (
#    'oii.workflow.celery_broadcast.wakeup',
#)

CELERY_QUEUES = (Broadcast('wakeup'), )
CELERY_ROUTES = {
    WAKEUP_TASK: {
        'queue': 'wakeup'
    }
}

