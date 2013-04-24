import logging
import pika
import sys
import re

DEFAULT_BROKER_URL='amqp://guest:guest@localhost:5672/%2f'

def declare_log_exchange(exchange,routing_key='',broker_url=DEFAULT_BROKER_URL):
    """Declare a "log exchange"
    A log exchange is a fanout exchange. Should be consumed with no_ack=True"""
    connection = pika.BlockingConnection(pika.URLParameters(broker_url))
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange,exchange_type='fanout')
    return channel, connection

class RabbitLogHandler(logging.Handler):
    def __init__(self,level=logging.NOTSET,exchange='logs',routing_key='',broker_url=DEFAULT_BROKER_URL):
        logging.Handler.__init__(self,level=level) # old-style superclass chaining
        self.broker_url = broker_url
        self.exchange = exchange
        self.routing_key = routing_key
        self.channel = None
    def emit(self,record):
        formatted = self.format(record)
        if self.channel is None:
            self.channel, _ = declare_log_exchange(self.exchange, self.routing_key, self.broker_url)
        self.channel.basic_publish(exchange=self.exchange,routing_key=self.routing_key,body=formatted)
    def consume(self,out=sys.stdout,callback=None):
        ch, _ = declare_log_exchange(self.exchange,self.routing_key,self.broker_url)
        result = ch.queue_declare(exclusive=True)
        qname = result.method.queue
        ch.queue_bind(exchange=self.exchange,queue=qname)
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
    broker_url = 'amqp://guest:guest@localhost:5672/%2f'
    handler = RabbitLogHandler(broker_url=broker_url)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    if sys.argv[1] == 'produce':
        for n in range(20):
            time.sleep(random.random())
            logger.info('logging message %d' % n)
    elif sys.argv[1] == 'consume':
        handler.consume()
