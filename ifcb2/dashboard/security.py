import random, string
from flask import Blueprint
from flask_user import login_required, roles_required, current_user

def maketoken():
    s = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choice(s) for _ in range(40))

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


