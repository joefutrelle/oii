from flask import Flask, Blueprint, request
import json
import flask.ext.restless
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User, Role, Instrument
from oii.ifcb2.session import session, dbengine
from flask.ext.user import UserManager, SQLAlchemyAdapter
from oii.ifcb2.dashboard.security import roles_required, current_user

app = Flask(__name__)

# add app security configurations and setup setup user_manager
# this is being done so we can use the user_manager.hash_password() function
# below, without trying to cross-import from app.py
app.config.from_object('oii.ifcb2.dashboard.config.flask_user')
db_adapter = SQLAlchemyAdapter(dbengine, User)
user_manager = UserManager(db_adapter,app)

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    print "*************************************************"
    print data
    print "*************************************************"
    if data.has_key('edit'):
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        data.pop('edit')

def admin_api_auth(instance_id=None, data=None, **kw):
    "Raise 401 if user is not logged in our does not have Admin role."
    allow = False
    if current_user.is_authenticated() and current_user.has_roles('Admin'):
        allow = True
    if not allow:
        raise flask.ext.restless.ProcessingException('Not Authorized',401)

manager = flask.ext.restless.APIManager(app, session=session)

# assign admin_api_auth to all preprocessors
preprocessors = {
    'GET_SINGLE': [admin_api_auth],
    'GET_MANY': [admin_api_auth],
    'PATCH_SINGLE': [admin_api_auth, patch_single_preprocessor],
    'PATCH_MANY': [admin_api_auth, patch_single_preprocessor],
    'PATCH': [admin_api_auth, patch_single_preprocessor],
    'POST': [admin_api_auth],
    'DELETE':[admin_api_auth, patch_single_preprocessor]
    }

timeseries_blueprint = manager.create_api_blueprint(
    TimeSeries,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors
    )
manager_blueprint = manager.create_api_blueprint(
    DataDirectory,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors
    )
instrument_blueprint = manager.create_api_blueprint(
    Instrument,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors
    )
user_blueprint = manager.create_api_blueprint(
    User,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    exclude_columns=['password',]
    )
role_blueprint = manager.create_api_blueprint(
    Role,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    exclude_columns=['password',]
    )

password_blueprint = Blueprint('password', __name__)

@password_blueprint.route('/setpassword/<int:instid>', methods=['POST'])
@roles_required('Admin')
def set_password(instid):
    data = json.loads(request.data)
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    # should eventually perform check in password complexity
    if data.has_key('password') and data['password']:
        user.password = user_manager.hash_password(data['password'])
        session.commit()
        return "password updated for user %s" % user.email, 200
    else:
        return "missing password", 400








