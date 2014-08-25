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

from oii.times import text2utcdatetime
from oii.resolver import parse_stream
from oii.times import text2utcdatetime

Base = declarative_base()

class TimeSeries(Base):
    __tablename__ = 'time_series'

    name = Column(String, primary_key=True)
    description = Column(String, default='')
    enabled = Column(Boolean, default=True)

    def __repr__(self):
        return "<TimeSeries '%s'>" % self.name

class DataDirectory(Base):
    __tablename__ = 'data_dirs'

    id = Column(Integer, primary_key=True)
    time_series = Column(String, ForeignKey('time_series.name'))
    path = Column(String)
    ts = relationship("TimeSeries",
                      backref=backref('data_dirs', cascade="all, delete-orphan", order_by=id))

    def __repr__(self):
        return "<DataDirectory '%s'>" % self.path

class Bin(Base):
    __tablename__ = 'bins'

    lid = Column(String, primary_key=True)
    sample_time = Column(DateTime(timezone=True))
    skip = Column(Boolean)

    def __init__(self, lid, sample_time, skip=False):
        self.lid = lid
        self.sample_time = sample_time
        self.skip = skip

    def __repr__(self):
        return '<Bin %s>' % self.lid

class File(Base):
    __tablename__ = 'fixity'

    lid = Column(String, ForeignKey('bins.lid'), primary_key=True)
    length = Column(BigInteger)
    filename = Column(String)
    filetype = Column(String, primary_key=True)
    sha1 = Column(String)
    fix_time = Column(DateTime(timezone=True))
    local_path = Column(String)

    bin = relationship('Bin', backref=backref('files',order_by=lid))

    def __init__(self, lid, length, filename, filetype, sha1, fix_time, local_path):
        self.lid = lid
        self.length = length
        self.filename = filename
        self.filetype = filetype
        self.sha1 = sha1
        self.fix_time = fix_time
        self.local_path = local_path

    def __repr__(self):
        return '<File %s %d %s>' % (self.filename, self.length, self.sha1)

class User(Base):
    __tablename__ = 'users'

    email = Column(String,primary_key=True)
    name = Column(String)
    password = Column(String)
    admin = Column(Boolean, default=False)
    superadmin = Column(Boolean, default=False)
    apiuser = Column(Boolean, default=False)

    def __repr__(self):
        return "<User(email='%s')>" % self.email

# utilities - FIXME refactor

def time_range(session, start_time, end_time):
    return session.query(Bin).\
        filter(and_(Bin.sample_time >= start_time, Bin.sample_time <= end_time)).\
        order_by(Bin.sample_time)
