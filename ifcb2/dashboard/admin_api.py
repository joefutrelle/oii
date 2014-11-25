from flask import Blueprint, request
import json
import flask.ext.restless
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User, Role
from oii.ifcb2.orm import Instrument, APIKey
from oii.ifcb2.dashboard.security import roles_required, current_user, maketoken
from oii.ifcb2.dashboard.flasksetup import app, manager, session, user_manager
from passlib.hash import sha256_crypt

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

# assign admin_api_auth to all preprocessors
preprocessors = {
    'GET_SINGLE': [admin_api_auth],
    'GET_MANY': [admin_api_auth],
    'PATCH_SINGLE': [admin_api_auth, patch_single_preprocessor],
    'PATCH_MANY': [admin_api_auth, patch_single_preprocessor],
    'PATCH': [admin_api_auth, patch_single_preprocessor],
    'POST': [admin_api_auth, patch_single_preprocessor],
    'DELETE':[admin_api_auth]
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
    )
keychain_blueprint = manager.create_api_blueprint(
    APIKey,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET','DELETE'],
    preprocessors=preprocessors,
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

@password_blueprint.route('/genkey/<int:instid>', methods=['POST'])
@roles_required('Admin')
def genkey(instid):
    data = json.loads(request.data)
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    # should eventually perform check in password complexity
    if data.has_key('name') and data['name']:
        key = APIKey()
        key.name = data['name']
        key.user = user
        token = maketoken()
        key.token = token #encrypt later
        session.add(key)
        session.commit()
        return json.dumps({'token':token})
    else:
        return "missing key name", 400









