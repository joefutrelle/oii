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
from sqlalchemy.orm import relationship, backref
from flask.ext.user import UserMixin

from oii.times import text2utcdatetime
from oii.resolver import parse_stream
from oii.times import text2utcdatetime
from oii.utils import remove_extension
from oii.orm_utils import fix_utc
from oii.ifcb2 import HDR, ADC, ROI, HDR_PATH, ADC_PATH, ROI_PATH

FILE_CHECKSUM='sha1'
FILE_LENGTH='length'
FILE_EXISTS='exists'
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

    @property
    def destination_dirs(self):
        return filter(lambda dd: dd.destination, self.data_dirs)

class DataDirectory(Base):
    __tablename__ = 'data_dirs'

    id = Column(Integer, primary_key=True)
    time_series_id = Column(Integer, ForeignKey('time_series.id'))
    product_type = Column(String, default='raw')
    path = Column(String)
    destination = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    time_series = relationship('TimeSeries',
                               backref=backref('data_dirs', cascade="all, delete-orphan", order_by=(priority, id)))

    def __repr__(self):
        return "<DataDirectory '%s'>" % self.path

class Bin(Base):
    __tablename__ = 'bins'

    id = Column(Integer, primary_key=True)
    ts_label = Column(String)
    lid = Column(String, index=True, unique=True)
    sample_time = Column(DateTime(timezone=True), index=True)
    skip = Column(Boolean, default=False)

    triggers = Column(Integer,default=0)
    duration = Column(Numeric,default=0)
    temperature = Column(Numeric,default=0)
    humidity = Column(Numeric,default=0)

    def __repr__(self):
        return '<Bin %s:%s @ %s>' % (self.ts_label, self.lid, self.sample_time)

    @property
    def trigger_rate(self):
        if self.duration is None or self.duration<0.1:
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
            FILE_EXISTS: False,
            FILE_LENGTH: False,
            FILE_CHECKSUM: False
        }
        if os.path.exists(self.local_path):
            status[FILE_EXISTS] = True
            if fast:
                sha1 = CHECKSUM_PLACEHOLDER
            else:
                sha1 = sha1_file(self.local_path)
            status[FILE_CHECKSUM] = self.sha1==sha1
            status[FILE_LENGTH] = self.length==os.stat(self.local_path).st_size
        return status

class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer,primary_key=True)
    name = Column(String,unique=True)
    data_path = Column(String)
    last_polled = Column(DateTime(timezone=True))
    time_series_id = Column(Integer, ForeignKey('time_series.id'))

    time_series = relationship('TimeSeries')

class User(Base, UserMixin):
    """data model must conform to flask-user expectations here
    http://pythonhosted.org/Flask-User/data_models.html#all-in-one-user-datamodel"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    # User Authentication information
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(255), nullable=False, default='')
    reset_password_token = Column(String(100), nullable=False, default='')
    # User Email information
    email = Column(String(255), nullable=False, unique=True)
    confirmed_at = Column(DateTime())
    # User information
    is_enabled = Column(Boolean(), nullable=False, default=False)
    first_name = Column(String(50), nullable=False, default='')
    last_name = Column(String(50), nullable=False, default='')

    roles = relationship('Role', secondary='user_roles',
                backref=backref('users', lazy='dynamic'))
    # the scoped_session property is bound here in order to provide
    # compatibility between our Users orm class and the Flask-Users module
    #query = ScopedSession.query_property()
    # FIXED, deferred until app configuration time

    def is_active(self):
      return self.is_enabled

    def __repr__(self):
        return "<User(email='%s')>" % self.email

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer(), primary_key=True)
    name = Column(String(50), unique=True)
    #query = ScopedSession.query_property()

class UserRoles(Base):
    __tablename__ = 'user_roles'
    id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.id', ondelete='CASCADE'))
    role_id = Column(Integer(), ForeignKey('roles.id', ondelete='CASCADE'))
    users = relationship('User')
    roles = relationship('Role')
    #query = ScopedSession.query_property()

class APIKey(Base):
    __tablename__ = 'api_keys'
    id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False, unique=True)
    token = Column(String(255), nullable=False, unique=True)
    datetime_late_user = Column(DateTime(timezone=True), nullable=True, default=None)
    datetime_created = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow())

    user = relationship("User", backref=backref('api_keys', order_by=id))




