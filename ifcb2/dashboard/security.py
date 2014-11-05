from flask import Blueprint
from flask.ext import login
from flask.ext import user

class SecurityConfig(object):
    USER_PASSWORD_HASH_MODE = 'passlib'
    USER_PASSWORD_HASH      = 'bcrypt'
    SECRET_KEY              = 'adoijfaeo@@@@@^^^^1284u'

login_manager = login.LoginManager()

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
def user():
    return "<h3>IFCB user test page.</h3>"

@security_blueprint.route('/test_admin')
def admin():
    return "<h3>IFCB admin test page.</h3>"


