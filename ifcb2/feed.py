from datetime import datetime

from sqlalchemy import and_, or_, not_, desc, func

from oii.times import utcdtnow, datetime2utcdatetime
from oii.ifcb2.orm import Bin, File

def _time_range_params(start_time=None, end_time=None):
    if start_time is None:
        start_time = datetime.utcfromtimestamp(0)
    if end_time is None:
        end_time = datetime.utcfromtimestamp(2147483647)
    return start_time, end_time

def time_range(session, start_time=None, end_time=None):
    start_time, end_time = _time_range_params(start_time, end_time)
    return session.query(Bin).\
        filter(and_(Bin.sample_time >= start_time, Bin.sample_time <= end_time, ~Bin.skip)).\
        order_by(Bin.sample_time)

def daily_data_volume(session, start_time=None, end_time=None):
    start_time, end_time = _time_range_params(start_time, end_time)
    return session.query(func.sum(File.length), func.DATE(Bin.sample_time)).\
        filter(and_(Bin.sample_time >= start_time, Bin.sample_time <= end_time, ~Bin.skip)).\
        filter(Bin.id==File.bin_id).\
        group_by(func.DATE(Bin.sample_time)).\
        order_by(func.DATE(Bin.sample_time))

def nearest(session,timestamp=None,n=1):
    """timestamp must be a utc datetime, defaults to now"""
    if timestamp is None:
        timestamp = utcdtnow()
    n_before = session.query(Bin).\
        filter(and_(Bin.sample_time <= timestamp, ~Bin.skip)).\
        order_by(desc(Bin.sample_time)).\
        limit(n)
    min_date = datetime2utcdatetime(n_before[-1].sample_time)
    max_date = timestamp + (timestamp - min_date)
    n_after = session.query(Bin).\
        filter(and_(Bin.sample_time >= timestamp, Bin.sample_time <= max_date, ~Bin.skip)).\
        order_by(Bin.sample_time).\
        limit(n)
    cand = list(n_before) + list(n_after)
    return sorted(cand, key=lambda b: timestamp - datetime2utcdatetime(b.sample_time))[:n]

def latest(session,n=25,timestamp=None):
    """most recent. timestamp is optional and defaults to now"""
    if timestamp is None:
        timestamp = utcdtnow()
    return session.query(Bin).\
        filter(and_(Bin.sample_time <= timestamp, ~Bin.skip)).\
        order_by(desc(Bin.sample_time)).\
        limit(n)


