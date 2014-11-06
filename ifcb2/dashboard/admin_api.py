from flask import Flask, Blueprint, request
import json
import flask.ext.restless
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User
from oii.ifcb2.session import session, dbengine
from flask.ext.user import UserManager, SQLAlchemyAdapter

app = Flask(__name__)
# add app security configurations
app.config.from_object('oii.ifcb2.dashboard.security_config')

# setup user_manager
db_adapter = SQLAlchemyAdapter(dbengine, User)
user_manager = UserManager(db_adapter,app)


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

@password_blueprint.route('/setpassword/<int:instid>', methods=['POST'])
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








