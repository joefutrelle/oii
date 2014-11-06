from flask import Blueprint
from flask.ext import login
from flask.ext import user
from flask_user import login_required

security_blueprint = Blueprint('security', __name__)

@security_blueprint.route('/login')
def login():
    return "<h3>IFCB Login Page</h3>"

@security_blueprint.route('/logout')
def logout():
    return "<h3>IFCB Logout Page</h3>"

@security_blueprint.route('/test_public')
def public():
    return "<h3>IFCB public test page.</h3>"

@security_blueprint.route('/test_user')
@login_required
def user():
    return '<h3>IFCB user test page.</h3><br><br><a href="/user/sign-out">Logout</a>'

@security_blueprint.route('/test_admin')
@login_required
def admin():
    return "<h3>IFCB admin test page.</h3>"


