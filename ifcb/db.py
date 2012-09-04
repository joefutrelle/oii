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
    def latest_bins(self,date=None,n=25):
        """Return the LIDs of the n latest bins"""
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,sample_time from bins where sample_time <= %s order by sample_time desc limit %s",(dt,n)) # dangling comma is necessary
            for row in db.fetchall():
                yield row[0]
    def nearest_bin(self,date=None):
        if date is None:
            date = time.gmtime()
        dt = utcdatetime(date)
        with xa(self.psql_connect) as (c,db):
            db.execute("set session time zone 'UTC'")
            db.execute("select lid,@ extract(epoch from sample_time-%s) as time_delta from bins order by time_delta limit 1",(dt,))
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
            yield row[0]

class FixityError(Exception):
    pass

class IfcbFixity(Psql):
    def __init__(self,psql_connect,resolvers):
        super(IfcbFixity,self).__init__(psql_connect)
        self.time_threshold = 0
        self.resolvers = resolvers
    def compare(self, filename, fix_local_path, fix_length, sha1, fix_time):
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
        with xa(self.psql_connect) as (c,db):
            db.execute('select filename, local_path, length, sha1, extract(epoch from fix_time) from fixity')
            while True:
                batch = db.fetchmany()
                if len(batch) == 0:
                    break
                for row in batch:
                    (filename, local_path, length, sha1, fix_time) = row
                    self.compare(filename, local_path, length, sha1, fix_time)
    def summarize_data_volume(self):
        query = """
select
date_trunc('day',b.sample_time) as day, count(*)/3, sum(f.length)/1073741824.0 as gb
from bins b, fixity f
where b.lid=f.lid
group by day
order by day;
"""
        with xa(self.psql_connect) as (c,db):
            db.execute(query)
            return [dict(day=day.strftime('%Y-%m-%d'), bin_count=bin_count, gb=float(gb)) for (day,bin_count,gb) in db.fetchall()]

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
    fixity = IfcbFixity(config.psql_connect, resolvers)
    fixity.check_all()
