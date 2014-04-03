from flask import jsonify, abort, request, url_for
from flask.views import MethodView
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from models import TimeSeries, SystemPath

# IFCB restful configuration API
# written by Mark Nye (marknye@clubofhumanbeings.com), March 2014


# create db engine and database session
# do something better here later
from sqlalchemy.pool import StaticPool
dbengine = create_engine('sqlite://',
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()


class TimeSeriesAdminAPI(MethodView):
    "RESTful admin API for timeseries configurations"

    def _idToUri(self, ts):
        """Takes serialized TimeSeries instance. Returns instance with
        database ID replaced with usable URI."""
        if not ts.has_key('id'):
            return ts
        ts['uri'] = url_for(
            'adminapi.timeseries', timeseries_id=ts['id'], _external=True)
        ts.pop('id')
        return ts

    def get(self, timeseries_id):
        if timeseries_id is None:
            "return all timeseries configurations"
            return jsonify(
                timeseries=[self._idToUri(i.serialize) for i in session.query(TimeSeries).all()])
        else:
            "return a single timeseries configuration"
            ts = session.query(TimeSeries).filter_by(id=timeseries_id).one()
            if not ts:
                abort(404)
            return jsonify(timeseries=self._idToUri(ts.serialize))

    def post(self):
        "create a new timeseries configuration"
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
                try:
                    ts.systempaths.append(SystemPath(path = np))
                except:
                    session.rollback()
                    abort(400)
        try:
            session.commit()
        except:
            # something went wrong. rollback and report 400
            session.rollback()
            abort(400)
        return jsonify(timeseries=self._idToUri(ts.serialize))

    def put(self, timeseries_id):
        "update existing timeseries configuration"
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
                    try:
                        ts.systempaths.append(SystemPath(path = np))
                    except:
                        session.rollback()
                        abort(400)
        try:
            session.commit()
        except:
            # something went wrong. rollback and report 400
            session.rollback()
            abort(400)
        return jsonify(timeseries=self._idToUri(ts.serialize))

    def delete(self, timeseries_id):
        "delete timeseries configuration"
        ts = session.query(TimeSeries).filter_by(id=timeseries_id).one()
        if not ts:
            abort(404)
        try:
            session.delete(ts)
        except:
            # something went wrong. rollback and report 400
            session.rollback()
            abort(400)
        return jsonify( { 'result': True } )

