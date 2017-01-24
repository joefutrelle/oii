import random, string, json
from functools import wraps
from flask import Blueprint, request, Response, current_app
from flask_user import login_required, roles_required, current_user
from oii.ifcb2.orm import APIKey
from oii.ioutils import upload

from oii.rbac import AUTHORIZATION_HEADER

def maketoken():
    s = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choice(s) for _ in range(40))

def api_user():
    # unpack token from X-Authorization header
    token = request.headers.get(AUTHORIZATION_HEADER)
    if token and len(token) > 7 and token[0:7] == "Bearer ":
        token = token[7:].strip()
        try:
            session = current_app.config.get('SCOPED_SESSION')()
        except:
            session = current_app.config.get('SESSION') # FIXME broken
        apikey = session.query(APIKey).filter_by(token=token).first()
        if apikey:
            return apikey.user
    return None

def effective_user():
    user = api_user()
    if user is not None:
        return user
    return current_user
    
def api_key_has_user():
    return api_user() is not None

def api_key_has_roles(required_roles):
    user = api_user()
    if user and user.has_roles(*required_roles):
        return True
    return False

def logged_in():
    return current_user.is_authenticated()

def user_has_roles(required_roles):
    return logged_in() and current_user.has_roles(required_roles)

def authz_wrapper(*callbacks):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            authorized = False
            for callback in callbacks:
                if callback():
                    authorized = True
            if not authorized:
                r = {'message': 'Not Authorized'}
                return Response(json.dumps(r), status=401, mimetype='application/json')
            return func(*args, **kwargs)
        return decorated_view
    return wrapper

def api_required(func):
    return authz_wrapper(api_key_has_user)(func)

def api_login_required(func):
    return authz_wrapper(logged_in, api_key_has_user)(func)
    
def api_roles_required(*required_roles):
    return authz_wrapper(lambda: api_key_has_roles(required_roles))

def api_login_roles_required(*required_roles):
    return authz_wrapper(lambda: api_key_has_roles(required_roles) or user_has_roles(required_roles))

security_blueprint = Blueprint('security', __name__)

def test_page(description):
    r = """<h3>Test %s page</h3><br><br>
        <a href="/sec/login">Login</a>
        <a href="/sec/logout">Logout</a>""" % description
    return Response(r,mimetype='text/html')

@security_blueprint.route('/test_public')
def public():
    return "<h3>IFCB public test page.</h3>"
    
@security_blueprint.route('/test_login_required')
@login_required
def user():
    return test_page('login_required')

@security_blueprint.route('/test_api_required')
@api_required
def api():
    return test_page('api')

@security_blueprint.route('/test_api_login_required')
@api_login_required
def api_login():
    return test_page('api_login_required')
    
@security_blueprint.route('/test_roles_required')
@roles_required('Admin')
def admin():
    return test_page('roles_required (Admin)')

@security_blueprint.route('/test_api_roles_required')
@api_roles_required('Admin')
def admin_api():
    return test_page('api_roles_required (Admin)')
    
@security_blueprint.route('/test_api_login_roles_required')
@api_login_roles_required('Admin')
def admin_api_login():
    return test_page('api_login_roles_required')


