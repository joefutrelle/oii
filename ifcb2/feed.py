from datetime import datetime

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
        return self._ts_query(start_time, end_time).\
            order_by(Bin.sample_time)
    def daily_data_volume(self, start_time=None, end_time=None):
        start_time, end_time = _time_range_params(start_time, end_time)
        return self.session.query(cast(func.sum(File.length) / 1073741824.0, Numeric(6,2)), func.count(File.id) / 3, func.DATE(Bin.sample_time)).\
            filter(and_(Bin.ts_label==self.ts_label, Bin.sample_time >= start_time, Bin.sample_time <= end_time, ~Bin.skip)).\
            filter(Bin.id==File.bin_id).\
            group_by(func.DATE(Bin.sample_time)).\
            order_by(func.DATE(Bin.sample_time))
    def nearest(self,n=1,timestamp=None):
        """timestamp must be a utc datetime, defaults to now"""
        if timestamp is None:
            timestamp = utcdtnow()
        n_before = self._ts_query(end_time=timestamp).\
                   order_by(desc(Bin.sample_time)).\
                   limit(n)
        min_date = datetime2utcdatetime(n_before[-1].sample_time)
        max_date = timestamp + (timestamp - min_date)
        n_after = self._ts_query(start_time=timestamp, end_time=max_date).\
                  order_by(Bin.sample_time).\
                  limit(n)
        cand = list(n_before) + list(n_after)
        return sorted(cand, key=lambda b: timestamp - datetime2utcdatetime(b.sample_time))[:n]
    def latest(self,n=25,timestamp=None):
        if timestamp is None:
            timestamp = utcdtnow()
        return self._ts_query(end_time=timestamp).\
            order_by(desc(Bin.sample_time)).\
            limit(n)

