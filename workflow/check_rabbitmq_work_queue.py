
'''
Nagios plugin for checking a queue to make sure it's not backed up.
warning/critical thresholds are expressed in terms of number of pending jobs per consumer.
if there are no consumers and an empty queue, warn.
if there are no consumers and a non-empty queue, critical.
'''
import json
import urllib2 as urllib
import base64
import sys
import getopt

def usage():
    print '''Usage:
-w warning threshold
-c critical threshold
-u user:password
-h host:port
-v vhost
-q queue'''

'''example usage:
python check_rabbitmq_work_queue.py -h demi.whoi.edu:55672 -v / -w 2 -c 2 -u guest:guest -q blob_extraction
'''

def finish(message,exit_code):
    print message
    sys.exit(exit_code)
    
def ok(message):
    finish('OK - '+message, 0)
    
def warn(message):
    finish('WARNING - '+message, 1)

def critical(message):
    finish('CRITICAL - '+message, 2)
    
if __name__ == '__main__':
    '''Usage:
    -w warning threshold
    -c critical threshold
    -u user:password
    -h host:port
    -v vhost
    -q queue'''
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'w:c:u:h:v:q:')
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        sys.exit(2)
    opts = dict(optlist)
    warning = int(opts['-w'])
    crit = int(opts['-c'])
    (username, password) = opts['-u'].split(':')
    hostport = opts['-h']
    vhost = opts['-v']
    queue = opts['-q']
    url = 'http://%s/api/queues/%s/%s' % (hostport, urllib.quote(vhost, ''), queue)
    request = urllib.Request(url)
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    request.add_header('Authorization', 'Basic %s' % base64string)
    result = json.loads(urllib.urlopen(request).read())
    consumers = result['consumers']
    messages_ready = result['messages_ready']
    if consumers == 0 and messages_ready == 0:
        warn('Queue %s has no consumers and no pending jobs' % queue)
    elif consumers == 0 and messages_ready > 0:
        critical('Queue %s has %d pending jobs, but no consumers' % (queue, messages_ready))
    else:
        mpc = float(messages_ready) / consumers
        message = 'Queue %s has %d messages ready, %d consumers (%f msgs/consumer)' % (queue, messages_ready, consumers, mpc)
        if mpc >= crit:
            critical(message)
        elif mpc >= warning:
            warn(message)
        else:
            ok(message)

