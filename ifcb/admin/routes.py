import os

from flask import Flask, Blueprint, send_from_directory
from handlers import TimeSeriesAdminAPI

from config import BASEPATH

# create flask app
app = Flask(__name__)
app.debug = True

# create blueprints
adminapi = Blueprint('adminapi', __name__, url_prefix=BASEPATH)
adminstatic = Blueprint('adminstatic', __name__)

# add static files
@adminstatic.route('/admin/<path:filename>')
def serve_static(filename):
    # set path to static content dynamically
    # this may need to change later
    fp = "%s/static" % os.path.dirname(os.path.realpath(__file__))
    return send_from_directory(fp, filename)


# build api view
timeseries_view = TimeSeriesAdminAPI.as_view('timeseries_api')

adminapi.add_url_rule(
    '/timeseries/',
    defaults={'timeseries_id': None},
    view_func=timeseries_view,
    methods=['GET',])
adminapi.add_url_rule(
    '/timeseries/',
    view_func=timeseries_view,
    methods=['POST',])
adminapi.add_url_rule(
    '/timeseries/<int:timeseries_id>',
    view_func=timeseries_view,
    methods=['GET', 'PUT', 'DELETE'],
    endpoint='timeseries')


if __name__=='__main__':
    # import a few needed modules to start the development server
    # and initialize the database
    from handlers import dbengine, session
    from models import Base, TimeSeries, SystemPath
    Base.metadata.create_all(dbengine)
    ts = TimeSeries(name = 'testseries1',enabled = False)
    path = SystemPath(path = '/Users/marknye')
    ts.systempaths.append(path)
    session.add(ts)
    session.commit()
    app.register_blueprint(adminapi)
    app.register_blueprint(adminstatic)
    print app.url_map
    app.run(host='0.0.0.0',port=8080,threaded=False)
