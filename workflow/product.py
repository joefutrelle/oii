from oii.times import secs2utcdatetime, dt2utcdt

STATES=['new','waiting','running','available','failed','halted','blacklisted']
EVENTS=['create','ready','start','retry','restart','finish','blacklist']
STATE_TRANSITIONS = {
    None: {'create': 'new'},
    'new': {'ready': 'start'},
    'waiting': {'start': 'running'},
    'running': {'stop': 'halted',
                'fail': 'failed',
                'finish': 'available'},
    'halted': {'restart': 'waiting'},
    'failed': {'retry': 'waiting',
               'blacklist': 'blacklisted'},
    'available': {'restart': 'waiting'}
}

def ProductException(Exception):
    pass

class Product(object):
    def __init__(self,pid,status=None,event=None,ts=None):
        self.pid = pid
        self.status = status
        self.event = event
        self.ts = ts
    def event(self, event='new', ts=None):
        if event not in EVENTS:
            raise ProductException('unknown event %s' % event)
        if ts is None:
            ts = secs2utcdatetime() # now
        try:
            new_status = STATE_TRANSITIONS[self.state][event]
            self.status = new_status
            self.event = event
            self.ts = ts
        except KeyError:
            raise ProductException('illegal state transition: state=%s event=%s' % (self.state, event))
        
