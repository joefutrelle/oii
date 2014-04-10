
import flask
import flask.ext.sqlalchemy
import flask.ext.restless
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, TimeSeries, SystemPath


app = flask.Flask(__name__)
app.config['DEBUG'] = True

from sqlalchemy.pool import StaticPool
dbengine = create_engine('sqlite://',
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    if data.has_key('edit'):
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        print "*************************************************"
        print data
        print "*************************************************"
        data.pop('edit')

manager = flask.ext.restless.APIManager(app, session=session)
manager.create_api(
    TimeSeries,
    url_prefix='/admin/api/v1',
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE': [patch_single_preprocessor], 'POST':[patch_single_preprocessor]})
manager.create_api(
    SystemPath,
    url_prefix='/admin/api/v1',
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor] })


if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    ts = TimeSeries(name = 'Pond Water',enabled = False)
    path = SystemPath(path = '/Users/marknye')
    path2 = SystemPath(path = '/Users/marknye/Documents')
    ts.systempaths.append(path)
    ts.systempaths.append(path2)
    session.add(ts)
    ts2 = TimeSeries(name = 'Ocean Water',enabled = False)
    path3 = SystemPath(path = '/Users/marknye/Desktop')
    ts2.systempaths.append(path3)
    session.add(ts2)
    session.commit()
    print app.url_map
    app.run(host='0.0.0.0',port=8080)



