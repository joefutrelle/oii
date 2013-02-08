import logging
import time
import json
import datetime

from oii.psql import xa
from oii.iopipes import LocalFileSource
from oii.ifcb.db import IfcbFeed, IfcbFixity
from oii.resolver import parse_stream
from oii.ifcb.formats import integrity
from oii.times import text2utcdatetime

from celery import Celery

celery = Celery('oii.ifcb.accession')

RESOLVER_FILE='oii/ifcb/mvco.xml'
PSQL_CONNECT='user=testing password=********* dbname=ditylum'

def list_adcs(time_series,after_year=2012):
    r = parse_stream(RESOLVER_FILE) # FIXME hardcoded
    for s in r['list_adcs'].resolve_all(time_series=time_series): # FIXME hardcoded
        date = time.strptime(s.date, s.date_format)
        if date.tm_year > after_year:
            yield s
        else:
            logging.info('%s SKIP, out of date range' % s.pid)

def list_new_filesets(time_series,after_year=2012):
    feed = IfcbFeed(PSQL_CONNECT) # FIXME hardcoded
    r = parse_stream(RESOLVER_FILE) # FIXME hardcoded
    for s in list_adcs(time_series,after_year):
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
    time_series='ditylum'
    logging.basicConfig(level=logging.INFO)
    fx = IfcbFixity(PSQL_CONNECT) # FIXME
    feed = IfcbFeed(PSQL_CONNECT) # FIXME hardcoded
    with xa(PSQL_CONNECT) as (c, db):
        for s in list_new_filesets(time_series,after_year=2011):
            try:
                check_integrity(s.pid, s.hdr_path, s.adc_path, s.roi_path, s.schema_version)
            except Exception, e:
                logging.warn('%s FAIL integrity checks: %s' % (s.pid, e))
                break
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
                break
            # register bin
            try:
                ts = text2utcdatetime(s.date, s.date_format)
                feed.create(s.pid, ts, cursor=db)
                c.commit()
                logging.info('%s DONE' % s.pid)
            except:
                logging.error('%s FAILED' % s.pid)
                break
