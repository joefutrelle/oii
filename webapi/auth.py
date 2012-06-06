from flask import Blueprint, request, session, abort
import json

# this blueprint provides the /authenticate endpoint for an app

# for various reasons we can't call the blueprint instance, the function, and the source file
# all the same thing: "auth". So we have three names:
# module: auth
# blueprint: auth_api
# function: authenticate
# so the url_for call is url_for('auth_api.authenticate')

auth_api = Blueprint('auth_api', __name__)
auth_api.auth_callback = lambda u,p: True

@auth_api.route('/authenticate',methods=['POST'])
def authenticate():
    (u,p) = (request.form['username'], request.form['password'])
    if auth_api.auth_callback(u,p):
        session['username'] = u
        return json.dumps(dict(username=u))
    else:
        abort(401)
