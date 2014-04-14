import sys
import logging
import time
import json
import datetime

from oii.resolver import parse_stream
from oii.ifcb.db import IfcbFeed
from oii.utils import gen_id
from oii.config import get_config

from oii.ifcb.workflow.blob_extraction import extract_blobs

# example config file
# resolver = oii/ifcb/mvco.xml
# [ditylum]
# psql_connect = user=foobar password=bazquux dbname=ditylum

CONFIG_FILE = './blob.conf'

def enqueue_blobs(time_series,queue):
    """config needs psql_connect, resolver"""
    config = get_config(CONFIG_FILE, time_series)
    feed = IfcbFeed(config.psql_connect)
    r = parse_stream(config.resolver)
    blob_resolver = r['mvco_blob']
    pid_resolver = r['pid']
    for lid in feed.latest_bins(n=10000):
        if blob_resolver.resolve(pid=lid,time_series=time_series) is None:
            pid = pid_resolver.resolve(pid=lid,time_series=time_series).bin_pid
            print 'No blobs found for %s, enqueuing' % pid
            extract_blobs.apply_async(args=[time_series, pid],queue=queue)

if __name__=='__main__':
    time_series = sys.argv[1]
    try:
        queue = sys.argv[2]
    except:
        queue = '_'.join([time_series,'blobs'])
    enqueue_blobs(time_series,queue)
