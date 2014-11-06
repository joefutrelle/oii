
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, scoped_session


# eventually the session cofiguration should
# go in its own class.
#SQLITE_URL='sqlite:///home/ubuntu/dev/ifcb_admin.db'
SQLITE_URL='sqlite:///ifcb_admin.db'

dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                         echo=False)
ScopedSession = scoped_session(sessionmaker(bind=dbengine))
session = ScopedSession()
