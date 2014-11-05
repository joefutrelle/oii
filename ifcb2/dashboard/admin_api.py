from flask import Flask, Blueprint
import flask.ext.restless
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User
from oii.ifcb2.session import session
from flask.ext.user import UserManager

app = Flask(__name__)

def patch_single_preprocessor(instance_id=None, data=None, **kw):
    print "*************************************************"
    print data
    print "*************************************************"
    if data.has_key('edit'):
        # remove restangularize "edit" field. probably a better way
        # to do this on the javascript side
        data.pop('edit')

manager = flask.ext.restless.APIManager(app, session=session)

timeseries_blueprint = manager.create_api_blueprint(
    TimeSeries,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE': [patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
manager_blueprint = manager.create_api_blueprint(
    DataDirectory,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor]}
    )
user_blueprint = manager.create_api_blueprint(
    User,
    #url_prefix=API_URL_PREFIX,
#    validation_exceptions=[DBValidationError],
    methods=['GET', 'POST', 'DELETE','PATCH'],
    preprocessors={'PATCH_SINGLE':[patch_single_preprocessor], 'POST':[patch_single_preprocessor], 'PATCH':[patch_single_preprocessor],},
    exclude_columns=['password',]
    )

password_blueprint = Blueprint('password', __name__)

@password_blueprint.route('/users/<int:instid>/setpassword', methods=['POST'])
def set_password(instid):
    user = session.query(User).filter_by(id=instid).first()
    if not user:
        return "User not found", 404
    # should eventually perform check in password complexity
    if request.form.has_key('password') and request.form['password']:
        user.password = UserManager().hash_password(request.form['password'])
        session.commit()
        return "password updated for user %s" % user.email, 200
    else:
        return "missing password", 400








