import flask
import flask.ext.sqlalchemy
import flask.ext.restless
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oii.ifcb2.orm import Base, TimeSeries, DataDirectory, User

app = flask.Flask(__name__)
app.config['DEBUG'] = True

# eventually the session cofiguration should
# go in its own class.
#SQLITE_URL='sqlite:///home/ubuntu/dev/ifcb_admin.db'
SQLITE_URL='sqlite:///ifcb_admin.db'

from sqlalchemy.pool import StaticPool
dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

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
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE': [patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    DataDirectory,
    url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager.create_api(
    User,
    url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )

def demo_data():
    # add testing data
    ts = TimeSeries(label='pond', description= 'Pond Water',enabled = False)
    path = DataDirectory(path = '/Users/marknye')
    path2 = DataDirectory(path = '/Users/marknye/Documents')
    ts.data_dirs.append(path)
    ts.data_dirs.append(path2)
    session.add(ts)
    ts2 = TimeSeries(label='ocean', description = 'Ocean Water',enabled = False)
    path3 = DataDirectory(path = '/Users/marknye/Desktop')
    ts2.data_dirs.append(path3)
    session.add(ts2)
    user = User(name='Joe Futrelle',email='joe@schneertz.com',superadmin=True)
    user2 = User(name='Mark Nye',email='marknye@chb.com',admin=True)
    session.add(user)
    session.add(user2)
    session.commit()

if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    print app.url_map # FIXME debug
    app.run(host='0.0.0.0',port=8080)

"""
# add blueprints later
adminapi = Blueprint('adminapi', __name__, url_prefix=BASEPATH)
adminstatic = Blueprint('adminstatic', __name__)
app.register_blueprint(adminapi)
app.register_blueprint(adminstatic)
"""


















