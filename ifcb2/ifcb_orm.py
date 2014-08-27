import os
from datetime import timedelta, datetime
import calendar
import time

import pytz

import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import and_, or_, desc
from sqlalchemy.sql.expression import func

from oii.times import text2utcdatetime, datetime2utcdatetime
from oii.utils import sha1_file
from oii.ifcb2 import get_resolver
from oii.ifcb2.identifiers import parse_pid
from oii.ifcb2.orm import Base, TimeSeries, DataDirectory, Bin, File, User

def time_range(session, start_time, end_time):
    return session.query(Bin).\
        filter(and_(Bin.sample_time >= start_time, Bin.sample_time <= end_time)).\
        order_by(Bin.sample_time)

demo_end_time = text2utcdatetime('2013-09-20T00:00:00Z')
demo_start_time = demo_end_time - timedelta(hours=2)

# time range demo
def time_range_demo(session):
    print '2 hours worth of bins:'
    for instance in time_range(session, demo_start_time, demo_end_time):
        print instance

# now extend this to show files

def files_demo(session):
    print '2 hours worth of files:'
    for instance in time_range(session, demo_start_time, demo_end_time):
        print instance.files

def data_volume_demo(session):
    print 'data volume per day'
    for row in session.query(func.sum(File.length), func.DATE(Bin.sample_time)).\
        filter(Bin.id==File.bin_id).\
        group_by(func.DATE(Bin.sample_time)).\
        order_by(func.DATE(Bin.sample_time)).\
        limit(7):
        print row

def nearest_demo(session):
    ts = '2013-09-10T13:45:22Z'
    somedate = text2utcdatetime(ts)
    n = 5
    print '%d nearest bins to %s' % (n,ts)
    n_before = session.query(Bin).\
        filter(Bin.sample_time <= somedate).\
        order_by(desc(Bin.sample_time)).\
        limit(n)
    min_date = datetime2utcdatetime(n_before[-1].sample_time)
    max_date = somedate + (somedate - min_date)
    n_after = session.query(Bin).\
        filter(and_(Bin.sample_time >= somedate, Bin.sample_time <= max_date)).\
        order_by(Bin.sample_time).\
        limit(n)
    cand = list(n_before) + list(n_after)
    print sorted(cand, key=lambda b: somedate - datetime2utcdatetime(b.sample_time))[:n]

def query_demo(session):
    time_range_demo(session)
    files_demo(session)
    data_volume_demo(session)
    nearest_demo(session)

# accession
def accession_demo(session,root):
    # now accede
    for fs in get_resolver().ifcb.files.list_raw_filesets(root):
        lid = fs['lid']
        try:
            parsed = parse_pid(lid)
        except:
            print 'barf %s' % lid
            raise
        ts = text2utcdatetime(parsed['timestamp'], parsed['timestamp_format'])
        b = Bin(lid=lid, sample_time=ts)
        session.add(b)
        # now make mostly bogus fixity entries
        now = datetime.now()
        paths = [fs['hdr_path'], fs['adc_path'], fs['roi_path']]
        filetypes = ['hdr','adc','roi']
        for path,filetype in zip(paths,filetypes):
            length = os.stat(path).st_size
            name = os.path.basename(path)
            #checksum = sha1_file(path)
            checksum = 'placeholder'
            f = File(local_path=path, filename=name, length=length, filetype=filetype, sha1=checksum, fix_time=now)
            b.files.append(f)
    session.commit()

def get_sqlite_engine(delete=True):
    # first, toast db
    DB_FILE = 'test.db'
    if(delete):
        try:
            os.remove(DB_FILE)
        except:
            pass
    return sqla.create_engine('sqlite:///%s' % DB_FILE)

def get_psql_engine():
    return sqla.create_engine('postgresql://ifcb:ifcb@localhost/testdb')

def timeseries_demo(session):
    ts = TimeSeries(label='ts_one',description='First time series')
    ts.data_dirs.append(DataDirectory(path='/tmp/foo'))
    ts.data_dirs.append(DataDirectory(path='/blah/fnord'))
    user = User(name='Joe Futrelle',email='jfutrelle@whoi.edu')
    session.add(ts)
    session.add(user)
    session.commit()
    for ts in session.query(TimeSeries):
        print ts
        print ts.data_dirs
    for u in session.query(User):
        print u

def bin_demo(session):
    bin = Bin(lid='foo', sample_time=datetime.now())
    session.add(bin)
    session.commit()

if __name__=='__main__':
    engine = get_sqlite_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    timeseries_demo(session)
    #accession_demo(session,'/mnt/data/okeanos')
    #query_demo(session)
