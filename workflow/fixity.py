import os
import time
from oii.times import secs2utcdatetime, datetime2utcdatetime
from oii.utils import sha1_file, md5_file

class FixityException(Exception):
    pass

class Fixity(object):
    def __init__(self,pid,pathname,length=None,checksum=None,fix_time=None,create_time=None,mod_time=None,checksum_type='md5',fix=True):
        """all timestamps should be datetimes with timezone"""
        self.pid = pid
        self.pathname = pathname
        self.filename = os.path.basename(pathname)
        self.length = length
        self.checksum = checksum
        self.checksum_type = checksum_type
        self.fix_time = datetime2utcdatetime(fix_time)
        self.create_time = datetime2utcdatetime(create_time)
        self.mod_time = datetime2utcdatetime(mod_time)
        if fix:
            self.fix()
    def __repr__(self):
        return '<Fixity pid=%s path=%s length=%d checksum(%s)=%s as of %s>' % \
            (self.pid, self.pathname, self.length, self.checksum_type, self.checksum, self.fix_time)
    def fix(self):
        """compute fixity based on pathname"""
        now = secs2utcdatetime(time.time())
        stat = os.stat(self.pathname)
        self.length = stat.st_size
        self.fix_time = now
        self.create_time = secs2utcdatetime(stat.st_ctime)
        self.mod_time = secs2utcdatetime(stat.st_mtime)
        if self.checksum_type=='md5':
            self.checksum = md5_file(self.pathname)
        elif self.checksum_type=='sha1':
            self.checksum = sha1_file(self.pathname)
    def check(self):
        """check fixity against current state of pathname.
        failure modes include missing file, non-matching length and checksum."""
        if not os.path.exists(self.pathname):
            raise FixityException("file not found at location specified in fixity record")
        stat = os.stat(self.pathname)
        if stat.st_size != self.length:
            raise FixityException("file size differs from fixity record")
        if self.checksum_type=='md5':
            if self.checksum != md5_file(self.pathname):
                raise FixityException("md5 checksum does not match fixity record")
        elif self.checksum_type=='sha1':
            if self.checksum != sha15_file(self.pathname):
                raise FixityException("sha-1 checksum does not match fixity record")

        

