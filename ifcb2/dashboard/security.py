import random, string, json
from functools import wraps
from flask import Blueprint, request, Response
from flask_user import login_required, roles_required, current_user
from oii.ifcb2.dashboard.flasksetup import session
from oii.ifcb2.orm import APIKey

def maketoken():
    s = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choice(s) for _ in range(40))

def api_roles_required(*required_roles):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            # default auth status is faluse
            authorized = False
            # unpack token from Authorization header
            token = request.headers.get('Authorization')
            if token and len(token) > 7 and token[0:7] == "Bearer ":
                token = token[7:].strip()
                apikey = session.query(APIKey).filter_by(token=token).first()
                if apikey:
                    if apikey.user.has_roles(*required_roles):
                        # the submitted token has been matched to a user
                        # with the required roles. mark status as authorized
                        authorized = True
            # not not authorized, stop request processing and
            # return json 401
            if not authorized:
                return Response(
                    json.dumps({"message": "Not Authorized"}),
                    status=401, mimetype='application/json')

            return func(*args, **kwargs)
        return decorated_view
    return wrapper

security_blueprint = Blueprint('security', __name__)

@security_blueprint.route('/test_public')
def public():
    return "<h3>IFCB public test page.</h3>"

@security_blueprint.route('/test_user')
@login_required
def user():
    return '<h3>IFCB user test page.</h3><br><br><a href="/sec/logout">Logout</a>'

@security_blueprint.route('/test_admin')
@roles_required('Admin')
def admin():
    return '<h3>IFCB admin test page.</h3><br><br><a href="/sec/logout">Logout</a>'

@security_blueprint.route('/test_admin_api')
@api_roles_required('Admin')
def admin_api():
    return '<h3>IFCB admin api test page.</h3><br><br><a href="/sec/logout">Logout</a>'


