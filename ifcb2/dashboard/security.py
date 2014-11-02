from flask import Blueprint
from flask.ext import login
from flask.ext import user

login_manager = login.LoginManager()

security_blueprint = Blueprint('security', __name__)

@security_blueprint.route('/login')
def login():
    return "<h3>IFCB Login Page</h3>"

@security_blueprint.route('/logout')
def logout():
    return "<h3>IFCB Logout Page</h3>"


