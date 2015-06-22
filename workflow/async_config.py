from kombu.common import Broadcast

from oii.workflow.async import WAKEUP_TASK

WAKEUP_QUEUE='async_wakeup'

CELERY_QUEUES = (Broadcast(WAKEUP_QUEUE),)
CELERY_ROUTES = { WAKEUP_TASK: { 'queue': WAKEUP_QUEUE } }

