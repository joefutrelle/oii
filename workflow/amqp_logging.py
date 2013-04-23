import logging
import pika
import sys

def configure(host='localhost',port=5672):
    return pika.ConnectionParameters(host=host,port=port)

def declare_log_exchange(exchange,routing_key='',connection_params=None):
    """Declare a "log exchange"
    A log exchange is a fanout exchange. Should be consumed with no_ack=True"""
    if connection_params is None:
        connection_params = configure()
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange,type='fanout')
    return channel, connection

class RabbitLogHandler(logging.Handler):
    def __init__(self,level=logging.NOTSET,exchange='logs',routing_key='',connection_params=None):
        logging.Handler.__init__(self,level=level) # old-style superclass chaining
        self.connection_params = connection_params
        if self.connection_params is None:
            self.connection_params = configure()
        self.exchange = exchange
        self.routing_key = routing_key
        self.channel = None
    def emit(self,record):
        formatted = self.format(record)
        if self.channel is None:
            self.channel, _ = declare_log_exchange(self.exchange, self.routing_key)
        self.channel.basic_publish(exchange=self.exchange,routing_key=self.routing_key,body=formatted)

def consume_log(exchange='logs',routing_key='',out=sys.stdout,callback=None,connection_params=None):
    if connection_params is None:
        connection_params = configure()
    ch, _ = declare_log_exchange(exchange,routing_key,connection_params=connection_params)
    result = ch.queue_declare(exclusive=True)
    qname = result.method.queue
    ch.queue_bind(exchange=exchange,queue=qname)
    def printer(ch,m,p,b):
        out.write(b.rstrip()+'\n')
        out.flush()
    if callback is None:
        callback = printer
    ch.basic_consume(callback,queue=qname,no_ack=True)
    ch.start_consuming()

import random
import time

if __name__=='__main__':
    logger = logging.getLogger('foobaz')
    logger.addHandler(RabbitLogHandler())
    logger.setLevel(logging.DEBUG)
    if sys.argv[1] == 'produce':
        for n in range(100):
            time.sleep(random.random())
            logger.info('logging message %d' % n)
    elif sys.argv[1] == 'consume':
        consume_log()
