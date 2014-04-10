
from os.path import isdir
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref


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
        return path
        if not isdir(path):
            raise ValueError('directory path is not readable on system')
        return path

    def __repr__(self):
        return "<SystemPath(path='%s')>" % self.path
