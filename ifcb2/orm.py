import os
from datetime import timedelta, datetime
from oii.utils import sha1_file
import calendar
import time

import pytz

from sqlalchemy import Column, ForeignKey, and_, or_, desc
from sqlalchemy import Integer, BigInteger, String, DateTime, Boolean, Numeric
from sqlalchemy.sql.expression import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref

from oii.times import text2utcdatetime
from oii.resolver import parse_stream
from oii.times import text2utcdatetime
from oii.orm_utils import fix_utc

CHECKSUM_PLACEHOLDER='(placeholder)'

Base = declarative_base()

# make sure all timestamps roundtrip as UTC
fix_utc(Base)

class TimeSeries(Base):
    __tablename__ = 'time_series'

    id = Column(Integer, primary_key=True)
    label = Column(String, unique=True)
    description = Column(String, default='')
    enabled = Column(Boolean, default=True)
    live = Column(Boolean, default=False)

    def __repr__(self):
        return "<TimeSeries '%s'>" % self.label

class DataDirectory(Base):
    __tablename__ = 'data_dirs'

    id = Column(Integer, primary_key=True)
    time_series_id = Column(Integer, ForeignKey('time_series.id'))
    product_type = Column(String, default='raw')
    path = Column(String)
    time_series = relationship('TimeSeries',
                      backref=backref('data_dirs', cascade="all, delete-orphan", order_by=id))

    def __repr__(self):
        return "<DataDirectory '%s'>" % self.path

class Bin(Base):
    __tablename__ = 'bins'

    id = Column(Integer, primary_key=True)
    ts_label = Column(String)
    lid = Column(String, unique=True)
    sample_time = Column(DateTime(timezone=True))
    skip = Column(Boolean, default=False)

    triggers = Column(Integer)
    duration = Column(Numeric)
    temperature = Column(Numeric)
    humidity = Column(Numeric)

    def __repr__(self):
        return '<Bin %s:%s @ %s>' % (self.ts_label, self.lid, self.sample_time)

    @property
    def trigger_rate(self):
        if self.duration is None:
            return 0
        else:
            return self.triggers / self.duration

class File(Base):
    __tablename__ = 'fixity'

    id = Column(Integer, primary_key=True)
    bin_id = Column(Integer, ForeignKey('bins.id'))
    length = Column(BigInteger)
    filename = Column(String)
    filetype = Column(String)
    sha1 = Column(String)
    fix_time = Column(DateTime(timezone=True))
    local_path = Column(String)

    bin = relationship('Bin', backref=backref('files',order_by=id))

    def __repr__(self):
        return '<File %s %d %s>' % (self.filename, self.length, self.sha1)

    def compute_fixity(self,fast=False):
        """compute fixity, overwriting existing fixity"""
        """requires that local_path is correct"""
        self.fix_time = datetime.now()
        self.length = os.stat(self.local_path).st_size
        self.filename = os.path.basename(self.local_path)
        # skip checksumming, because it's slow
        if fast:
            self.sha1 = CHECKSUM_PLACEHOLDER
        else:
            self.sha1 = sha1_file(self.local_path)

    def check_fixity(self,fast=False):
        status = {
            'exists': False,
            'length': False,
            'filename': False,
            'sha1': False
        }
        if os.path.exists(self.local_path):
            if fast:
                sha1 = CHECKSUM_PLACEHOLDER
            else:
                sha1 = sha1_file(self.local_path)
            status['sha1'] = self.sha1==sha1
            status['length'] = self.length==os.state(self.local_path).st_size
        return status

class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer,primary_key=True)
    name = Column(String,unique=True)
    data_path = Column(String)
    last_polled = Column(DateTime(timezone=True))
    time_series_id = Column(Integer, ForeignKey('time_series.id'))

    time_series = relationship('TimeSeries')

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer,primary_key=True)
    email = Column(String,unique=True)
    name = Column(String)
    password = Column(String)
    admin = Column(Boolean, default=False)
    superadmin = Column(Boolean, default=False)
    apiuser = Column(Boolean, default=False)

    def __repr__(self):
        return "<User(email='%s')>" % self.email
