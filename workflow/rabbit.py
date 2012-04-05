import pika
import sys
import re

# statuses
PASS='pass' # non-fatal, requeue (queue browsing)
WIN='win' # success, put in win queue
FAIL='fail' # fatal, dead-letter

# handy properties
PERSISTENT=pika.BasicProperties(delivery_mode=2)

def debug(message):
    #print message
    pass

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

def log(message,ename,host='localhost'):
    """Log a message to a log exchange"""
    ch, cn = declare_log_exchange(ename,host)
    ch.basic_publish(exchange=ename,routing_key='',body=message)
    cn.close()

def enqueue(message,qname,host='localhost'):
    """Push a message into a work queue"""
    ch, cn = declare_work_queue(qname,host)
    ch.basic_publish(exchange='', routing_key=qname, body=message, properties=PERSISTENT)
    cn.close()

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

class Job(object):
    """A RabbitMQ worker class
    Implement run_callback to return a status message such as WIN, FAIL, or PASS"""
    def __init__(self,qname,host='localhost'):
        self.host = host
        self.qname = qname
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
        log(message,self.qname+'_log',self.host)
    def enqueue(self,message,qname=None):
        """Put a message in this worker's queue"""
        if qname is None:
            qname = self.qname
        debug('enqueue %s to %s' % (message,qname))
        enqueue(message,qname,self.host)
    def work(self):
        """Start doing work. Will not return as it blocks for messages"""
        def amqp_run_callback(channel, method, properties, message):
            debug('callback %s' % message)
            try:
                ret = self.run_callback(message)
                debug('callback %s returned %s' % (message,ret))
                if ret == PASS:
                    reject(channel,method,requeue=False)
                    self.enqueue(message)
                elif ret == WIN or ret is None:
                    ack(channel,method)
                    self.enqueue(message,self.qname+'_win')
                elif ret == FAIL:
                    raise
            except:
                reject(channel,method)
                self.enqueue(message,self.qname+'_fail')
                raise
        ch,_ = declare_work_queue(self.qname, self.host)
        ch.basic_consume(amqp_run_callback, queue=self.qname)
        ch.start_consuming()
    def retry_failed(self):
        """Push failed tasks back into the work queue"""
        def requeue_callback(channel, method, properties, message):
            self.enqueue(message)
            ack(channel,method)
        ch,_ = declare_work_queue(self.qname, self.host)
        ch.basic_consume(requeue_callback, queue=self.qname+'_fail')
        ch.start_consuming()
    def consume_log(self,out=sys.stdout):
        """Consume the log and send it to the given output stream.
        Will not return as it blocks for incoming log messages"""
        ename = self.qname + '_log'
        ch, cn = declare_log_exchange(ename,self.host)
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
        ptFoo.work()
    elif command == 'bar':
        ptBar.work()
    elif command == 'log':
        ptFoo.consume_log()

