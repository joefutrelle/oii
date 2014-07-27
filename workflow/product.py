from oii.times import secs2utcdatetime, dt2utcdt

def ProductException(Exception):
    pass

class Product(object):
    def __init__(self,pid,state=None,event=None,ts=None):
        self.pid = pid
        self.state = state
        self.event = event
        self.ts = ts
        self.depends_on = []
        if self.state is None:
            self.changed('create')
    def __repr__(self):
        return '<Product %s (%s)>' % (self.pid, self.state)
    def changed(self, event='create', state='new', ts=None):
        if ts is None:
            ts = secs2utcdatetime() # now
        self.state = state
        self.event = event
        self.ts = ts
    @property
    def ancestors(self):
        for parent in self.depends_on:
            yield parent
            for anc in parent.ancestors:
                yield anc
