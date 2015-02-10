import sys
import cmd

from oii.utils import asciitable

# command-line client for workflow
from oii.workflow import PID, STATE, EVENT, MESSAGE, TS
from oii.workflow import DOWNSTREAM, STATE, UPSTREAM, ROLE, WAITING
from oii.workflow.client import WorkflowClient

PRODUCT_COLS=[PID, STATE, EVENT, TS, MESSAGE]
DEP_COLS=[DOWNSTREAM, STATE, UPSTREAM, ROLE]

def print_product(d):
    t = [{'Property':k,'Value':v} for k,v in d.items()]
    for line in asciitable(t,disp_cols=['Property','Value']):
        print line

def print_products(r):
    for line in asciitable(r,disp_cols=PRODUCT_COLS):
        print line

def print_deps(r):
    for line in asciitable(r,disp_cols=DEP_COLS):
        print line

class WorkflowShell(cmd.Cmd):
    def __init__(self, client):
        cmd.Cmd.__init__(self) # oldstyle class
        self.client = client
    def do_find(self,args):
        frag = args
        r = self.client.search(frag)
        print_products(r)
    def do_graph(self,args):
        pid = args
        r = self.client.get_graph(pid)
        print_deps(r)
    def _error(self,r):
        print 'Server responded with %d' % r.status_code
    def _show(self,pid):
        d = self.client.get(pid)
        print_product(d)
    def do_show(self,pid):
        self._show(pid)
    def do_set(self,args):
        (v,o,pid) = args.split(' ')
        if v=='state':
            self.client.update(pid,state=o)
        elif v=='event':
            self.client.update(pid,event=o)
        elif v=='message':
            self.client.update(pid,message=o)
        elif v=='ttl':
            self.client.update(pid,ttl=o)
        else:
            print 'unrecognized property %s' % v
            return
        self._show(pid)
    def do_retry(self,pid):
        self.client.update(pid,state=WAITING)
        self.client.wakeup()
        self._show(pid)
    def do_wakeup(self,args):
        if args:
            self.client.wakeup(args)
            print 'woke up with key "%s"' % args
        else:
            self.client.wakeup()
            print 'woke up all'
    def do_recent(self,args):
        try:
            n = int(args)
        except:
            n = 10
        r = self.client.most_recent(n)
        print_products(r)
    def do_expire(self,args):
        n = self.client.expire()
        print '%d product(s) expired' % n
    def do_exit(self,args):
        sys.exit()
    def do_quit(self,args):
        sys.exit()

if __name__=='__main__':
    try:
        client = WorkflowClient(sys.argv[1])
    except:
        client = WorkflowClient()
    client.most_recent(1)
    client.most_recent(1)
    load_message = 'Workflow Service @ %s' % client.base_url
    cli = WorkflowShell(client).cmdloop(load_message)
