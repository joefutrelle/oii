from flask import Flask
import flask.ext.restless
from flask.ext.user import UserManager, SQLAlchemyAdapter
from oii.ifcb2.session import session, dbengine
from oii.ifcb2.orm import User
from oii.webapi.utils import UrlConverter, DatetimeConverter

# start the application
app = Flask(__name__)
app.url_map.converters['url'] = UrlConverter
app.url_map.converters['datetime'] = DatetimeConverter

# load Flask configuration file
app.config.from_object('oii.ifcb2.dashboard.config.flask_config')

# load RBAC configuration and init
# this gets us authn/authz and session management
app.config.from_object('oii.rbac.flask_user_config')
db_adapter = SQLAlchemyAdapter(dbengine, User)
user_manager = UserManager(db_adapter,app)

# create a Flask-Restless manager object
manager = flask.ext.restless.APIManager(app, session=session)


