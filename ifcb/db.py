from oii.psql import xa
import datetime
import pytz
import time

def utcdatetime(struct_time=time.time()):
    return datetime.datetime(*struct_time[:6], tzinfo=pytz.timezone('UTC'))

class IfcbFeed(object):
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect
    def latest_bins(self,n=25,date=None):
        """Return the LIDs of the n latest bins"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,sample_time from bins where sample_time <= %s order by sample_time desc limit %s",(dt,n)) # dangling comma is necessary
            for row in db.fetchall():
                yield row[0]
    def day_bins(self,date=None):
        """Return the LIDs of all bins on the given day"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,sample_time from bins where date_part('year',sample_time) = %s and date_part('month',sample_time) = %s and date_part('day',sample_time) = %s order by sample_time desc",(dt.year,dt.month,dt.day))
        for row in db.fetchall():
            yield ifcb.pid(row[0])
