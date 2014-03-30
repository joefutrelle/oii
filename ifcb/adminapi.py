from flask import Flask, jsonify, abort, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.exc import IntegrityError

# IFCB restful configuration API
# written by Mark Nye (marknye@clubofhumanbeings.com), March 2014

# config (refactor later)
BASEPATH = '/admin/api/v1.0'

# configuration database mapping
# this will also need to be refactored, but keep in one file for now
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
    path = Column(String, unique=True)
    timeseries = relationship("TimeSeries",
        backref=backref('systempaths', cascade="all, delete-orphan", order_by=id))

    @property
    def serialize(self):
        return self.path

    def __repr__(self):
        return "<SystemPath(path='%s')>" % self.path


def validate_path(path):
    pass

# create flask app
app = Flask(__name__)
app.debug = True

# create db engine and database session
# do something better here later
from sqlalchemy.pool import StaticPool
dbengine = create_engine('sqlite://',
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()


@app.route(BASEPATH + '/timeseries', methods = ['GET'])
# return all timeseries configurations
def get_timeseries_list():
    return jsonify(
        timeseries=[i.serialize for i in session.query(TimeSeries).all()])

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['GET'])
# return select timeseries configuration
def get_timeseries(timeseries_id):
    ts = session.query(TimeSeries).filter_by(id=timeseries_id).one()
    if not ts:
        abort(404)
    return jsonify(timeseries=ts.serialize)

@app.route(BASEPATH + '/timeseries', methods = ['POST'])
# create timeseries configuration
def create_timeseries():
    print request.json
    if not request.json:
        abort(400)
    if not 'name' in request.json or not 'enabled' in request.json:
        abort(400)
    ts = TimeSeries(
        name = request.json['name'],
        enabled = request.json['enabled']
        )
    session.add(ts)
    if 'systempaths' in request.json:
        for np in request.json['systempaths']:
            ts.systempaths.append(SystemPath(path = np))
    try:
        session.commit()
    except:
        session.rollback()
        abort(400)
    return jsonify(timeseries=ts.serialize)


@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['PUT'])
# update timeseries configuration
def update_timeseries(timeseries_id):
    if not request.json:
        abort(400)
    ts = session.query(TimeSeries).filter_by(id=timeseries_id).one()
    if not ts:
        abort(404)
    if 'name' in request.json:
        ts.name = request.json['name']
    if 'enabled' in request.json:
        ts.enabled = request.json['enabled']
    if 'systempaths' in request.json:
        # sync paths
        eps = [ep.path for ep in ts.systempaths]
        for ep in ts.systempaths:
            if ep.path not in request.json['systempaths']:
                session.delete(ep)
        for np in request.json['systempaths']:
            if np not in eps:
                ts.systempaths.append(SystemPath(path = np))
    try:
        session.commit()
    except:
        session.rollback()
        abort(400)
    return jsonify(timeseries=ts.serialize)

@app.route(BASEPATH + '/timeseries/<int:timeseries_id>', methods = ['DELETE'])
# delete timeseries configuration
def delete_timeseries(timeseries_id):
    ts = session.query(TimeSeries).filter_by(id=timeseries_id).one()
    if not ts:
        abort(404)
    try:
        session.delete(ts)
    except:
        session.rollback()
        abort(400)
    return jsonify( { 'result': True } )


if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    ts = TimeSeries(name = 'testseries1',enabled = False)
    path = SystemPath(path = '/foo/foo')
    ts.systempaths.append(path)
    session.add(ts)
    session.commit()
    app.run(host='0.0.0.0',port=8080,threaded=False)
