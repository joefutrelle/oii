
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, scoped_session

# this should move to a global config file
SQLITE_URL='sqlite:///ifcb_admin.db'

dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                         echo=True)
# scoped sessions are enabled here in order to provide
# compatibility between our Users orm class and the Flask-Users module
ScopedSession = scoped_session(sessionmaker(bind=dbengine))
session = ScopedSession()
