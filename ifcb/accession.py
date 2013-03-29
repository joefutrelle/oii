import sys
import logging
import time
import json
import datetime

from oii.config import get_config
from oii.psql import xa
from oii.iopipes import LocalFileSource
from oii.ifcb.db import IfcbFeed, IfcbFixity
from oii.resolver import parse_stream
from oii.ifcb.formats import integrity
from oii.times import text2utcdatetime

#from celery import Celery

#celery = Celery('oii.ifcb.accession')

# example config file
# resolver = oii/ifcb/mvco.xml
# [ditylum]
# psql_connect = user=foobar password=bazquux dbname=ditylum

def list_adcs(time_series,resolver,after_year=2012):
    r = parse_stream(resolver)
    for s in r['list_adcs'].resolve_all(time_series=time_series): # FIXME hardcoded
        date = time.strptime(s.date, s.date_format)
        if date.tm_year > after_year:
            yield s
        else:
            logging.info('%s SKIP, out of date range' % s.pid)

def list_new_filesets(time_series,psql_connect,resolver,after_year=2012):
    feed = IfcbFeed(psql_connect)
    r = parse_stream(resolver)
    for s in list_adcs(time_series,resolver,after_year):
        if feed.exists(s.pid):
            logging.info('%s EXISTS in time series %s' % (s.pid, time_series))
        else:
            logging.info('%s NEW, not already in time series %s' % (s.pid, time_series))
            fs = r['fileset'].resolve(pid=s.pid,product='raw',time_series=time_series,day_dir=s.day_dir)
            if fs is None:
                logging.warn('%s UNRESOLVABLE cannot find raw files' % s.pid)
            else:
                yield fs

def check_integrity(pid, hdr_path, adc_path, roi_path, schema_version):
    integrity.check_hdr(LocalFileSource(hdr_path))
    logging.info('%s PASS integrity check %s' % (pid, hdr_path))
    targets = list(integrity.check_adc(LocalFileSource(adc_path), schema_version=schema_version))
    logging.info('%s PASS integrity check %s' % (pid, adc_path))
    integrity.check_roi(LocalFileSource(roi_path), targets)
    logging.info('%s PASS integrity check %s' % (pid, roi_path))

if __name__=='__main__':
    try:
        time_series=sys.argv[2]
        config = get_config(sys.argv[1], time_series)
    except:
        sys.stderr.write('usage: [python] oii/ifcb/accession.py [config file] [time series name]\n')
        sys.exit(-1)
    logging.basicConfig(level=logging.INFO)
    fx = IfcbFixity(config.psql_connect)
    feed = IfcbFeed(config.psql_connect)
    with xa(config.psql_connect) as (c, db):
        for s in list_new_filesets(time_series,config.psql_connect,config.resolver,after_year=2005): # FIXME hardcoded
            try:
                check_integrity(s.pid, s.hdr_path, s.adc_path, s.roi_path, s.schema_version)
            except Exception, e:
                logging.warn('%s FAIL integrity checks: %s' % (s.pid, e))
                continue
            # hot diggity, we've got some good data
            # compute fixity
            try:
                fx.fix(s.pid, s.hdr_path, cursor=db, filetype='hdr')
                logging.info('%s FIXITY computed for %s' % (s.pid, s.hdr_path))
                fx.fix(s.pid, s.adc_path, cursor=db, filetype='adc')
                logging.info('%s FIXITY computed for %s' % (s.pid, s.adc_path))
                fx.fix(s.pid, s.roi_path, cursor=db, filetype='roi')
                logging.info('%s FIXITY computed for %s' % (s.pid, s.roi_path))
            except:
                logging.error('%s FAIL fixity cannot be computed!' % s.pid)
                c.rollback()
                continue
            # register bin
            try:
                ts = text2utcdatetime(s.date, s.date_format)
                feed.create(s.pid, ts, cursor=db)
                c.commit()
                logging.info('%s DONE' % s.pid)
            except:
                logging.error('%s FAILED' % s.pid)
                continue

