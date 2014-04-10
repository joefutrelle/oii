
import flask
import flask.ext.sqlalchemy
import flask.ext.restless
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, TimeSeries, SystemPath, User, DBValidationError
from models import dbengine, session

app = flask.Flask(__name__)
app.config['DEBUG'] = False

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    if data.has_key('edit'):
        print "*************************************************"
        print data
        print "*************************************************"
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        data.pop('edit')

API_URL_PREFIX = '/admin/api/v1'

manager = flask.ext.restless.APIManager(app, session=session)
manager.create_api(
    TimeSeries,
    url_prefix=API_URL_PREFIX,
    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE': [patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    SystemPath,
    url_prefix=API_URL_PREFIX,
    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    User,
    url_prefix=API_URL_PREFIX,
    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )


if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    # add testing data
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
    user = User(name='Joe Futrelle',email='joe@schneertz.com',superadmin=True)
    user2 = User(name='Mark Nye',email='marknye@chb.com',admin=True)
    session.add(user)
    session.add(user2)
    session.commit()
    print app.url_map
    app.run(host='0.0.0.0',port=8080)



