import sys
import cmd

from oii.utils import asciitable

# command-line client for workflow
from oii.workflow.client import WorkflowClient, isok

def pprint(d):
    width = max(len(k) for k in d)
    print '{'
    for k in sorted(d):
        print '%s%s: "%s"' % (' ' * (width-len(k)),k,d[k])
    print '}'

class WorkflowShell(cmd.Cmd):
    def __init__(self, client):
        cmd.Cmd.__init__(self) # oldstyle class
        self.client = client
    def do_graph(self,args):
        pid = args
        r = self.client.get_dependencies(pid)
        if not isok(r):
            self._error(r)
            return
        for line in asciitable(r,disp_cols=['downstream','state','upstream','role']):
            print line
    def _error(self,r):
        print 'Server responded with %d' % r.status_code
    def _show(self,pid):
        r = self.client.get_product(pid)
        if not isok(r):
            self._error(r)
            return
        pprint(r.json())
    def do_show(self,pid):
        self._show(pid)
    def do_change(self,args):
        (v,o,pid) = args.split(' ')
        if v=='state':
            self.client.update(pid,state=o)
        elif v=='event':
            self.client.update(pid,event=o)
        elif v=='message':
            self.client.update(pid,message=o)
        else:
            print 'unrecognized property %s' % v
            return
        self._show(pid)
    def do_wakeup(self,args):
        if args:
            self.client.wakeup(args)
            print 'woke up with key "%s"' % args
        else:
            self.client.wakeup()
            print 'woke up all'
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
    load_message = 'Workflow Service @ %s' % client.base_url
    cli = WorkflowShell(client).cmdloop(load_message)
