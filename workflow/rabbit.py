import pika
from pika.adapters import SelectConnection
import sys
import re
import os
import traceback

from oii.utils import gen_id
from oii.times import iso8601
import platform

# statuses
PASS='pass' # non-fatal, requeue (queue browsing)
WIN='win' # success, put in win queue
FAIL='fail' # fatal, dead-letter
SKIP='skip' # non-fatal, drop message without any requeing. use for deduping queues
DIE='die' # worker cannot work, should requeue and terminate

# handy properties
PERSISTENT=pika.BasicProperties(delivery_mode=2)

DEBUG=False

def debug(message):
    if debug:
        print message

def declare_work_queue(qname,host='localhost'):
    """Declare a "work queue"
    A work queue is a durable queue with a prefetch_count of 1"""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.queue_declare(queue=qname, durable=True)
    channel.basic_qos(prefetch_count=1)
    return channel, connection

def declare_log_exchange(ename,host='localhost'):
    """Declare a "log exchange"
    A log exchange is a fanout exchange. Should be consumed with no_ack=True"""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.exchange_declare(exchange=ename,type='fanout')
    return channel, connection

def log(message,ename,host='localhost',channel=None):
    """Log a message to a log exchange"""
    if channel is None:
        ch, cn = declare_log_exchange(ename,host)
        ch.basic_publish(exchange=ename,routing_key='',body=message)
        cn.close()
    else:
        channel.basic_publish(exchange=ename,routing_key='',body=message)

def enqueue(message,qname,host='localhost'):
    """Push a message into a work queue"""
    ch, cn = declare_work_queue(qname,host)
    try:
        ch.basic_publish(exchange='', routing_key=qname, body=message.strip(), properties=PERSISTENT)
    except:
        for m in message:
            ch.basic_publish(exchange='', routing_key=qname, body=m, properties=PERSISTENT)
    cn.close()
        
# channel operations

def ack(channel,method):
    """Send a ack on the given channel.
    "method" is the method param passed to the RabbitMQ callback"""
    channel.basic_ack(delivery_tag=method.delivery_tag)

def nack(channel,method):
    """Send a nack on the given channel.
    "method" is the method param passed to the RabbitMQ callback"""
    channel.basic_nack(delivery_tag=method.delivery_tag)

def reject(channel,method,requeue=False):
    """Reject on the given channel.
    "method" is the method param passed to the RabbitMQ callback.
    requeue controls whether the message is pushed back to the queue it came from, in order"""
    channel.basic_reject(delivery_tag=method.delivery_tag, requeue=requeue)

class JobExit(Exception):
    def __init__(self, message, ret):
        self.message = message
        self.ret = ret
    def __str__(self):
        return '%s - %s' % (self.message, self.ret)

class Job(object):
    """A RabbitMQ worker class
    Implement run_callback to return a status message such as WIN, FAIL, or PASS"""
    def __init__(self,qname,host='localhost'):
        self.host = host
        self.qname = qname
        self.log_channel = None
        self.workerid = ('%s_%s' % (gen_id()[:4], platform.node()))
    def run_callback(self,message):
        """Override this method to do some work. Message is the queue entry received.
        Call log in this method to send messages to the log exchange.
        Return one of the following statuses:
        WIN - success
        PASS - this worker is unable to attempt this task
        FAIL - the worker failed to do the task
        You can also raise exceptions to indiciate failure"""
        return WIN
    def log(self,message):
        """Call this in run_callback to send messages to the log exchange"""
        debug('log %s' % message)
        ename = self.qname+'_log'
        if self.log_channel is None:
            self.log_channel, self.log_connection = declare_log_exchange(ename,self.host)
        prefix = '%s %s ' % (iso8601(), self.workerid)
        log(prefix + message,ename,channel=self.log_channel)
    def enqueue(self,message,qname=None):
        """Put a message in this worker's queue"""
        if qname is None:
            qname = self.qname
        debug('enqueue %s to %s' % (message,qname))
        enqueue(message,qname,self.host)
    def work(self,fork=False):
        """Start doing work. Will not return as it blocks for messages.
        If fork is true, will start in a separate process, wait for that process
        to terminate, and restart it when it does"""
        # callback handling WIN/PASS/FAIL queueing behavior
        def amqp_run_callback(channel, method, properties, message):
            debug('callback %s' % message)
            try:
                self.log('START %s' % message)
                ret = self.run_callback(message)
                self.log('CALLBACK %s returned %s' % (message,ret))
                raise JobExit(message, ret)
            except JobExit as e:
                message = e.message
                ret = e.ret
                if ret == PASS:
                    self.log('PASS - rejecting %s' % message)
                    reject(channel,method,requeue=False)
                    self.log('PASS - requeueing %s' % message)
                    self.enqueue(message)
                elif ret == WIN or ret is None:
                    self.log('WIN - acking %s' % message)
                    ack(channel,method)
                    self.log('WIN - recording win for %s' % message)
                    self.enqueue(message,self.qname+'_win')
                elif ret == SKIP:
                    self.log('SKIP - acking %s' % message)
                    ack(channel,method)
                elif ret == DIE:
                    self.log('DIE on %s - exiting' % message)
                    sys.exit(0)
                elif ret == FAIL:
                    self.log('FAIL - rejecting %s' % message)
                    reject(channel,method)
                    self.log('FAIL - recording fail for %s' % message)
                    self.enqueue(message,self.qname+'_fail')
            except KeyboardInterrupt:
                self.log('KEYBOARD INTERRUPT - rejecting %s' % message)
                reject(channel,method,requeue=True)
                raise
            except SystemExit:
                self.log('SYSTEM EXIT - rejecting %s' % message)
                reject(channel,method,requeue=True)
                sys.exit(0)
            except:
                self.log('EXCEPTION - rejecting %s' % message)
                reject(channel,method)
                self.log('EXCEPTION - recording fail for %s' % message)
                self.enqueue(message,self.qname+'_fail')
                raise
        # main loop
        pid = None
        while True:
            debug('waiting for jobs from %s' % self.qname)
            if fork and pid is None:
                pid = os.fork()
            if not fork or pid == 0:
                ch,_ = declare_work_queue(self.qname, self.host)
                ch.basic_consume(amqp_run_callback, queue=self.qname)
                ch.start_consuming()
            elif fork and pid != 0:
                try:
                    os.waitpid(pid,0)
                except KeyboardInterrupt:
                    sys.exit(0)
                except:
                    print 'WARNING exception while waiting for subprocess to terminate'
                pid = None
    def retry_failed(self, filter=lambda x: True):
        """Push failed tasks back into the work queue"""
        def requeue_callback(channel, method, properties, message):
            if filter(message):
                self.enqueue(message)
            ack(channel,method)
        ch,_ = declare_work_queue(self.qname, self.host)
        ch.basic_consume(requeue_callback, queue=self.qname+'_fail')
        ch.start_consuming()
    def consume_log(self,out=sys.stdout):
        """Consume the log and send it to the given output stream.
        Will not return as it blocks for incoming log messages"""
        ename = self.qname + '_log'
        ch, _ = declare_log_exchange(ename,self.host)
        result = ch.queue_declare(exclusive=True)
        qname = result.method.queue
        ch.queue_bind(exchange=ename,queue=qname)
        def printer(ch,m,p,b):
            out.write(b.rstrip()+'\n')
            out.flush()
        ch.basic_consume(printer,queue=qname,no_ack=True)
        ch.start_consuming()
     
# this class passes on messages that contain a certain string
class PassTest(Job):
    def __init__(self,qname,verboten='a',host='localhost'):
        super(PassTest,self).__init__(qname,host)
        self.verboten = verboten
    def run_callback(self,message):
        if re.match('.*%s.*' % self.verboten,message):
            self.log('%s PASS on %s' % (self.verboten, message))
            return PASS
        else:
            self.log('%s WIN on %s' % (self.verboten, message))

if __name__=='__main__':
    command = sys.argv[1]
    h = 'breakfast.whoi.edu'
    q = 'passtest'
    ptFoo = PassTest(q,'foo',h)
    ptBar = PassTest(q,'bar',h)
    if command == 'q':
        ptFoo.enqueue('food')
        ptFoo.enqueue('barbarians')
        ptFoo.enqueue('the bazzes')
        ptFoo.enqueue('meet me at the bar')
        ptFoo.enqueue('what fools you are')
        ptFoo.enqueue('I just passed my bar exam')
        ptFoo.enqueue('what the fooooo')
    elif command == 'r':
        ptFoo.retry_failed()
    elif command == 'foo':
        ptFoo.work(True)
    elif command == 'bar':
        ptBar.work(True)
    elif command == 'log':
        ptFoo.consume_log()

