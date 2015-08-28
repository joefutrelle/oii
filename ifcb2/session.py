
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, scoped_session

from dashboard_conf import DASHBOARD_DATABASE_URL

dbengine = create_engine(DASHBOARD_DATABASE_URL)
# scoped sessions are enabled here in order to provide
# compatibility between our Users orm class and the Flask-Users module
ScopedSession = scoped_session(sessionmaker(bind=dbengine))
session = ScopedSession()
