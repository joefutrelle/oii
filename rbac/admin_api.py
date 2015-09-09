from flask import Blueprint, request, current_app
from sys import stdout
import json
import flask.ext.restless
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User, Role
from oii.ifcb2.orm import Instrument, APIKey
from security import roles_required, current_user, maketoken
from oii.ifcb2.dashboard.flasksetup import manager, session, user_manager

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    if data.has_key('edit'):
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        data.pop('edit')
    if current_app.config['DEBUG']:
        # running in debug mode. show data
        stdout.write("request data: %s\n" % str(data))
        stdout.flush()

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
    preprocessors=preprocessors,
    results_per_page=None
    )
manager_blueprint = manager.create_api_blueprint(
    DataDirectory,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    results_per_page=None
    )
instrument_blueprint = manager.create_api_blueprint(
    Instrument,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    results_per_page=None
    )
user_blueprint = manager.create_api_blueprint(
    User,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    exclude_columns=['password'],
    results_per_page=None
    )
role_blueprint = manager.create_api_blueprint(
    Role,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors=preprocessors,
    results_per_page=None
    )
keychain_blueprint = manager.create_api_blueprint(
    APIKey,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET','DELETE'],
    preprocessors=preprocessors,
    results_per_page=None
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

user_admin_blueprint = Blueprint('user_admin', __name__)

@user_admin_blueprint.route('/delete_user/<int:instid>', methods=['POST'])
@roles_required('Admin')
def delete_user(instid):
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    session.delete(user)
    session.commit()
    return "user deleted", 200

@user_admin_blueprint.route('/patch_user/<int:instid>', methods=['POST'])
@roles_required('Admin')
def patch_user(instid):
    data = json.loads(request.data)
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    for k,v in data.items():
        try:
            if k not in ['id','password','roles']:
                setattr(user,k,v)
        except AttributeError:
            pass
    session.commit()
    return "user patched", 200

@user_admin_blueprint.route('/promote_user/<int:instid>', methods=['POST'])
@roles_required('Admin')
def promote_user(instid):
    user = session.query(User).filter_by(id=instid).first()
    adminRole = session.query(Role).filter_by(name='Admin').first()
    if not user:
        return "User not found", 404
    if not adminRole:
        return "Admin role not found", 404
    user.roles = [adminRole]
    session.commit()
    return "user promoted", 200

@user_admin_blueprint.route('/demote_user/<int:instid>', methods=['POST'])
@roles_required('Admin')
def demote_user(instid):
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    user.roles = []
    session.commit()
    return "user demoted", 200
