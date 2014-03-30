from flask import Flask
from handlers import TimeSeriesAdminAPI

# create flask app
app = Flask(__name__)
app.debug = True

# config (refactor later)
BASEPATH = '/admin/api/v1.0'

# configure routes
timeseries_view = TimeSeriesAdminAPI.as_view('timeseries_api')
app.add_url_rule(
    BASEPATH + '/timeseries/',
    defaults={'timeseries_id': None},
    view_func=timeseries_view,
    methods=['GET',])
app.add_url_rule(
    BASEPATH + '/timeseries/',
    view_func=timeseries_view,
    methods=['POST',])
app.add_url_rule(
    BASEPATH + '/timeseries/<int:timeseries_id>',
    view_func=timeseries_view,
    methods=['GET', 'PUT', 'DELETE'])


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
    app.run(host='0.0.0.0',port=8080,threaded=False)
