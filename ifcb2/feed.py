from datetime import datetime, timedelta

from sqlalchemy import and_, or_, not_, desc, func, cast, Numeric

from oii.times import utcdtnow, datetime2utcdatetime
from oii.ifcb2.orm import Bin, File

def _time_range_params(start_time=None, end_time=None):
    if start_time is None:
        start_time = datetime.utcfromtimestamp(0)
    if end_time is None:
        end_time = datetime.utcfromtimestamp(2147483647)
    return start_time, end_time

class Feed(object):
    """use with with"""
    def __init__(self, session, ts_label):
        self.session = session
        self.ts_label = ts_label
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        pass
    def _ts_query(self, start_time=None, end_time=None):
        start_time, end_time = _time_range_params(start_time, end_time)
        return self.session.query(Bin).filter(and_(\
            Bin.ts_label==self.ts_label,\
            Bin.sample_time >= start_time, Bin.sample_time <= end_time,\
            ~Bin.skip))
    def time_range(self, start_time=None, end_time=None):
        """all bins in a given time range"""
        return self._ts_query(start_time, end_time).\
            order_by(Bin.sample_time)
    def day(self, dt):
        day = dt.date()
        return self._ts_query(day, day + timedelta(days=1))
    def daily_data_volume(self, start_time=None, end_time=None):
        """data volume in GB per day over the given time range"""
        start_time, end_time = _time_range_params(start_time, end_time)
        return self.session.query(cast(func.sum(File.length) / 1073741824.0, Numeric(6,2)), func.count(File.id) / 3, func.DATE(Bin.sample_time)).\
            filter(and_(Bin.ts_label==self.ts_label, Bin.sample_time >= start_time, Bin.sample_time <= end_time, ~Bin.skip)).\
            filter(Bin.id==File.bin_id).\
            group_by(func.DATE(Bin.sample_time)).\
            order_by(func.DATE(Bin.sample_time))
    def nearest(self,n=1,timestamp=None):
        """nearest bin. timestamp must be a utc datetime, defaults to now"""
        if timestamp is None:
            timestamp = utcdtnow()
        n_before = self._ts_query(end_time=timestamp).\
                   order_by(desc(Bin.sample_time)).\
                   limit(n).all()
        min_date = datetime2utcdatetime(n_before[-1].sample_time)
        max_date = timestamp + (timestamp - min_date)
        n_after = self._ts_query(start_time=timestamp, end_time=max_date).\
                  order_by(Bin.sample_time).\
                  limit(n).all()
        cand = list(n_before) + list(n_after)
        return sorted(cand, key=lambda b: timestamp - datetime2utcdatetime(b.sample_time))[:n]
    def latest(self,n=25,timestamp=None):
        """most recent n bins from the given timestamp (defaults to now)"""
        if timestamp is None:
            timestamp = utcdtnow()
        return self._ts_query(end_time=timestamp).\
            order_by(desc(Bin.sample_time)).\
            limit(n)
    def after(self,bin_lid,n=1):
        """n bins after a given one"""
        return self.session.query(Bin).\
            filter(Bin.ts_label==self.ts_label).\
            filter(~Bin.skip).\
            filter(Bin.sample_time > self.session.query(Bin.sample_time).\
                   filter(Bin.lid==bin_lid).\
                   as_scalar()).\
            order_by(Bin.sample_time).\
            limit(n)
    def before(self,bin_lid,n=1):
        """n bins before a given one"""
        return self.session.query(Bin).\
            filter(Bin.ts_label==self.ts_label).\
            filter(~Bin.skip).\
            filter(Bin.sample_time < self.session.query(Bin.sample_time).\
                   filter(Bin.lid==bin_lid).\
                   as_scalar()).\
            order_by(desc(Bin.sample_time)).\
            limit(n)
    ## metrics
    def elapsed(self,timestamp=None):
        """time elapsed since latest bin at the given time (default now) (utc datetime).
        returns a timedelta"""
        if timestamp is None:
            timestamp = utcdtnow()
        latest = self.latest(1,timestamp)[0]
        return timestamp - latest.sample_time
