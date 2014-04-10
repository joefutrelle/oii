
from os.path import isdir
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool
dbengine = create_engine('sqlite://',
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

class DBValidationError(Exception):
    def __init__(self, message, errors):
        Exception.__init__(self, message)
        self.errors = errors


Base = declarative_base()


class TimeSeries(Base):

    __tablename__ = 'timeseries'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    enabled = Column(Boolean)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'enabled': self.enabled,
            'systempaths':self.serialize_paths
        }

    @property
    def serialize_paths(self):
        return [ i.serialize for i in self.systempaths]

    @validates('name')
    def validate_name(self, key, name):
        # flask-restless can't yet deal with unique=True database columns
        # so check for conflicting names with a validation dectorator
        q = session.query(TimeSeries).filter(TimeSeries.name == name)
        if self.id:
            q = q.filter(TimeSeries.id != self.id)
        if q.count():
            raise DBValidationError('validation error','The time series name "%s" already exists.' % name)
        return name

    def __repr__(self):
        return "<TimeSeries(name='%s')>" % self.name


class SystemPath(Base):

    __tablename__ = 'systempaths'
    id = Column(Integer, primary_key=True)
    timeseries_id = Column(Integer, ForeignKey('timeseries.id'))
    path = Column(String)
    timeseries = relationship("TimeSeries",
        backref=backref('systempaths', cascade="all, delete-orphan", order_by=id))

    @property
    def serialize(self):
        return self.path

    @validates('path')
    def validate_path(self, key, path):
        # skip val for now, improve later
        # return path
        if not isdir(path):
            raise DBValidationError('validation error','The path "%s" is not available.' % path)
        return path

    def __repr__(self):
        return "<SystemPath(path='%s')>" % self.path
