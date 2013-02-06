import logging
import time
import json
import datetime

from oii.psql import xa
from oii.iopipes import LocalFileSource
from oii.ifcb.db import IfcbFeed, IfcbFixity, fixity
from oii.resolver import parse_stream
from oii.ifcb.formats import integrity
from oii.times import text2utcdatetime

RESOLVER_FILE='oii/ifcb/mvco.xml'
PSQL_CONNECT='**************************************'

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

def check_integrity(fileset):
    integrity.check_hdr(LocalFileSource(s.hdr_path))
    logging.info('%s PASS integrity check' % s.hdr_path)
    targets = list(integrity.check_adc(LocalFileSource(s.adc_path), schema_version=s.schema_version))
    logging.info('%s PASS integrity check' % s.adc_path)
    integrity.check_roi(LocalFileSource(s.roi_path), targets)
    logging.info('%s PASS integrity check' % s.roi_path)

if __name__=='__main__':
    time_series='saltpond'
    logging.basicConfig(level=logging.INFO)
    fx = IfcbFixity(PSQL_CONNECT) # FIXME
    feed = IfcbFeed(PSQL_CONNECT) # FIXME hardcoded
    with xa(PSQL_CONNECT) as (c, db):
        for s in list_new_filesets(time_series,after_year=2011):
            try:
                check_integrity(s)
            except Exception, e:
                logging.warn('%s FAIL integrity checks: %s' % (s.pid, e))
            # hot diggity, we've got some good data
            # compute fixity
            fx.fix(s.pid, s.hdr_path, cursor=db)
            logging.info('computed fixity for %s' % s.hdr_path)
            fx.fix(s.pid, s.adc_path, cursor=db)
            logging.info('computed fixity for %s' % s.adc_path)
            fx.fix(s.pid, s.roi_path, cursor=db)
            logging.info('computed fixity for %s' % s.roi_path)
            # register bin
            ts = text2utcdatetime(s.date, s.date_format)
            feed.create(s.pid, ts, cursor=db)
            logging.info('recorded timestamp for %s' % s.pid)
        logging.info('committing changes to database...')
        db.commit()
