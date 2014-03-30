from flask import Flask, jsonify, abort
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref

# IFCB restful configuration API
# written by Mark Nye (marknye@clubofhumanbeings.com), March 2014

# config (refactor later)
BASEPATH = '/admin/api/v1.0'
DBENGINE = 'sqlite:///:memory:'

# configuration database mapping
# this will also need to be refactored, but keep in one file for now
Base = declarative_base()

class TimeSeries(Base):

    __tablename__ = 'timeseries'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    enabled = Column(Boolean)

    def __repr__(self):
        return "<TimeSeries(name='%s')" % self.name

class SystemPath(Base):

    __tablename__ = 'systempaths'
    id = Column(Integer, primary_key=True)
    timeseries_id = Column(Integer, ForeignKey('timeseries.id'))
    path = Column(String)

    timeseries = relationship("TimeSeries",
        backref=backref('systempaths', order_by=id))

    def __repr__(self):
        return "<SystemPath(path='%s')" % self.path


def validate_path(path):
    pass

# create flask app
app = Flask(__name__)
app.debug = True

# create db engine and database session
dbengine = create_engine(DBENGINE, echo=True)
Session = sessionmaker(bind=dbengine)


@app.route(BASEPATH + '/timeseries', methods = ['GET'])
# return all timeseries configurations
def get_timeseries_list():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['GET'])
# return select timeseries configuration
def get_timeseries(timeseries_id):
    pass

@app.route(BASEPATH + '/timeseries', methods = ['POST'])
# create timeseries configuration
def create_timeseries():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['PUT'])
# update timeseries configuration
def update_timeseries():
    pass

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['DELETE'])
# delete timeseries configuration
def delete_timeseries():
    pass


if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    app.run(host='0.0.0.0',port=8080)
