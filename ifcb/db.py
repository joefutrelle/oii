from oii.psql import xa
import datetime
import pytz
import time
import os
import re
from oii.times import iso8601
from oii.utils import sha1_file
from oii import resolver

def utcdatetime(struct_time=time.time()):
    return datetime.datetime(*struct_time[:6], tzinfo=pytz.timezone('UTC'))

class Psql(object):
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect

class IfcbFeed(Psql):
    def __init__(self,psql_connect):
        super(IfcbFeed,self).__init__(psql_connect)
        self.has_skip = None
    def skip_clause(self,kw='and'):
        if self.has_skip is None:
            with xa(self.psql_connect) as (c,db):
                db.execute("select 'skip' in (select column_name from information_schema.columns where table_name='bins')")
                self.has_skip = db.fetchall()[0][0]
        if self.has_skip:
            return '%s not skip' % kw
        else:
            return ''
    def exists(self,lid,skip=True):
        """Determines whether or not a bin exists"""
        with xa(self.psql_connect) as (c,db):
            if skip and self.has_skip:
                db.execute("select count(*) from bins where lid=%s and not skip",(lid,))
            else:
                db.execute("select count(*) from bins where lid=%s",(lid,))
            count = db.fetchone()[0]
            return count != 0
    def create(self,lid,ts,cursor=None):
        """Insert a bin into the time series.
        ts must be the correct timestamp for the bin; this function
        does not test that against the LID. it must be a datetime in UTC"""
        q = 'insert into bins (lid, sample_time) values (%s, %s)'
        if cursor is None:
            with xa(self.psql_connect) as (c,db):
                db.execute(q,(lid,ts))
                c.commit()
        else:
            cursor.execute(q,(lid,ts))
    def latest_bins(self,date=None,n=25):
        """Return the LIDs of the n latest bins"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,sample_time from bins where sample_time <= %s "+self.skip_clause()+" order by sample_time desc limit %s",(dt,n)) # dangling comma is necessary
            for row in db.fetchall():
                yield row[0]
    def nearest_bin(self,date=None):
        """Return the LID of the bin nearest the given time (or now if no time provided)"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,@ extract(epoch from sample_time-%s) as time_delta from bins "+self.skip_clause('where')+" order by time_delta limit 1",(dt,))
            for row in db.fetchall():
                yield row[0]
    def between(self,start=None,end=None):
        """Return the LIDs of all bins in the given time range
        (use None for start and/or end to leave the range open)"""
        if end is None:
            end = time.gmtime()
        if start is None:
            start = time.gmtime(0)
        start_dt = utcdatetime(start)
        end_dt = utcdatetime(end)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid from bins where sample_time >= %s and sample_time <= %s "+self.skip_clause(),(start_dt, end_dt))
            for row in db.fetchall():
                yield row[0]
    def before(self,lid,n=1):
        """Return the LIDs of n bins before the given one"""
        with xa(self.psql_connect) as (c,db):
            db.execute("select lid from bins where sample_time < (select sample_time from bins where lid=%s) "+self.skip_clause()+" order by sample_time desc limit %s",(lid,n))
            for row in db.fetchall():
                yield row[0]
    def after(self,lid,n=1):
        """Return the LIDs of n bins after the given one"""
        with xa(self.psql_connect) as (c,db):
            db.execute("select lid from bins where sample_time > (select sample_time from bins where lid=%s) "+self.skip_clause()+" order by sample_time asc limit %s",(lid,n))
            for row in db.fetchall():
                yield row[0]
    def day_bins(self,date=None):
        """Return the LIDs of all bins on the given day"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,sample_time from bins where date_part('year',sample_time) = %s and date_part('month',sample_time) = %s and date_part('day',sample_time) = %s "+self.skip_clause()+" order by sample_time desc",(dt.year,dt.month,dt.day))
        for row in db.fetchall():
            yield row[0]

class FixityError(Exception):
    pass

def compute_fixity(local_path):
    """Compute fixity for a given file"""
    filename = os.path.basename(local_path)
    length = os.stat(local_path).st_size
    fix_time = int(time.time())
    sha1 = sha1_file(local_path)
    return filename, length, sha1, fix_time

class IfcbFixity(Psql):
    def __init__(self,psql_connect,resolvers=None):
        super(IfcbFixity,self).__init__(psql_connect)
        self.time_threshold = 0
        self.resolvers = resolvers
    def compare(self, filename, fix_local_path, fix_length, sha1, fix_time):
        """Check a fixity entry against the current state of the data in the
        filesystem"""
        try:
            local_path = fix_local_path
            if not os.path.exists(fix_local_path):
                if self.resolvers is not None:
                    # use resolvers['binpid2path'] to try to find file
                    (bin_lid, format) = re.split(r'\.',filename)
                    hit = resolvers['binpid2path'].resolve(pid=bin_lid,format=format)
                    if hit is not None:
                        local_path = hit.value
                        print 'WARNING on %s: file has been moved to %s' % (fix_local_path, local_path)
                else:
                    raise FixityError('file is missing')
            file_stat = os.stat(local_path)
            file_length = file_stat.st_size
            file_time = file_stat.st_mtime
            time_delta = file_time - fix_time
            fix_date = iso8601(time.gmtime(fix_time))
            file_date = iso8601(time.gmtime(file_time))
            if fix_length != file_length:
                raise FixityError('file was %d bytes at fix time of %s, but is %d bytes as of %s' % (fix_length, fix_date, file_length, file_date))
            if local_path == fix_local_path and time_delta > self.time_threshold:
                checksum = sha1_file(local_path)
                if checksum != sha1:
                    raise FixityError('file modified at %s, after fix date of %s' % (file_date, fix_date))
                else:
                    raise FixityError('file touched at %s, after fix date of %s, but checksums match' % (file_date, fix_date))
        except KeyboardInterrupt:
            raise
        except FixityError as e:
            print 'FAILED on %s: %s' % (local_path,e)
    def check_all(self):
        """Check all fixity records in the time series. This can be a very time consuming
        operation"""
        with xa(self.psql_connect) as (c,db):
            db.execute('select filename, local_path, length, sha1, extract(epoch from fix_time) from fixity')
            while True:
                batch = db.fetchmany()
                if len(batch) == 0:
                    break
                for row in batch:
                    (filename, local_path, length, sha1, fix_time) = row
                    self.compare(filename, local_path, length, sha1, fix_time)
    def fix(self, lid, local_path, cursor=None, filetype='', fixity=None):
        if fixity is None:
            (filename, length, sha1, fix_time) = compute_fixity(local_path)
        values = (lid, length, filename, filetype, sha1, fix_time, local_path)
        q = "insert into fixity (lid, length, filename, filetype, sha1, fix_time, local_path) values (%s,%s,%s,%s,%s,%s::abstime::timestamp with time zone at time zone 'GMT',%s)"
        if cursor is None:
            with xa(self.psql_connect) as (c, db):
                db.execute(q,values)
                c.commit()
        else:
            cursor.execute(q,values)
    def summarize_data_volume(self):
        """Summarize data volume by day"""
        query = """
select
date_trunc('day',b.sample_time) as day, count(*)/3, (sum(f.length)/1073741824.0)::numeric(6,2) as gb
from bins b, fixity f
where b.lid=f.lid
group by day
order by day;
"""
        with xa(self.psql_connect) as (c,db):
            db.execute(query)
            return [dict(day=day.strftime('%Y-%m-%d'), bin_count=bin_count, gb=float(gb)) for (day,bin_count,gb) in db.fetchall()]

def time_range(start=None, end=None):
    if end is None:
        end = time.gmtime()
    if start is None:
        start = time.gmtime(0)
    start_dt = utcdatetime(start)
    end_dt = utcdatetime(end)
    return (start_dt, end_dt)

class IfcbAutoclass(Psql):
    def list_classes(self):
        with xa(self.psql_connect) as (c,db):
            db.execute('select distinct class_label from autoclass order by class_label')
            return [c[0] for c in db.fetchall()]
    def rois_of_class(self, class_label, start=None, end=None, threshold=0.0, page=1):
        PAGE_SIZE=10 # number of bins per page
        start_dt, end_dt = time_range(start, end)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
#            count_bins = "select count(*) from bins where sample_time >= %s and sample_time <= %s"
#            db.execute(count_bins,(start_dt,end_dt))
#            c = db.fetchall()[0][0]
#            if c == 0:
#                yield None
            query = """
select bin_lid, roinum from
(select bin_lid, unnest(roinums) as roinum, unnest(scores) as score from autoclass where bin_lid in
  (select lid from bins where sample_time >= %s and sample_time <= %s limit %s offset %s)
and class_label = %s) exploded
where score > %s
"""
            db.execute(query,(start_dt, end_dt, PAGE_SIZE, (page-1)*PAGE_SIZE, class_label, threshold))
            for row in db.fetchall():
                (bin_lid, roinum) = row
                yield '%s_%05d' % (bin_lid, roinum)
    def rough_count_by_day(self, class_label, start=None, end=None):
        query = """
select date_trunc('day',b.sample_time) as day,
sum(array_length(roinums,1))
from autoclass a, bins b
where a.bin_lid = b.lid
and sample_time >= %s and sample_time <= %s
and class_label = %s
group by day order by day
"""
        start_dt, end_dt = time_range(start, end)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute(query,(start_dt, end_dt, class_label))
            while True:
                batch = db.fetchmany()
                if len(batch) == 0:
                    break
                for row in batch:
                    (day, count) = row
                    yield {'day': day.strftime('%Y-%m-%d'), 'count': count }

class IfcbBinProps(Psql):
    def get_props(self,bin_lid):
        with xa(self.psql_connect) as (c,db):
            try:
                db.execute('select lat,lon,description from bin_props where lid=%s',(bin_lid,))
                (lat,lon,description) = db.fetchone()
                d = dict(lat=lat,lon=lon,description=description)
                for k in d.keys():
                    if d[k] is None:
                        del d[k]
                return d
            except:
                return {}

import sys
from oii.config import get_config, Configuration

if __name__=='__main__':
    if len(sys.argv) > 1:
        config = get_config(sys.argv[1])
    else:
        config = Configuration()
    try:
        resolvers = resolver.parse_stream(config.resolver)
    except:
        resolvers = None
    #fixity = IfcbFixity(config.psql_connect, resolvers)
    #fixity.check_all()
    autoclass = IfcbAutoclass(config.psql_connect)
    for roc in autoclass.rois_of_class('tintinnid'):
        print roc

