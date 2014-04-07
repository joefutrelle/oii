
import flask
import flask.ext.sqlalchemy
import flask.ext.restless
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, TimeSeries, SystemPath


app = flask.Flask(__name__)
app.config['DEBUG'] = True

from sqlalchemy.pool import StaticPool
dbengine = create_engine('sqlite://',
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

manager = flask.ext.restless.APIManager(app, session=session)
manager.create_api(TimeSeries, methods=['GET', 'PUT', 'POST', 'DELETE'])
manager.create_api(SystemPath, methods=['GET', 'POST', 'DELETE'])


if __name__=='__main__':
    Base.metadata.create_all(dbengine)
    ts = TimeSeries(name = 'testseries1',enabled = False)
    path = SystemPath(path = '/Users/marknye')
    ts.systempaths.append(path)
    session.add(ts)
    session.commit()
    session.add(ts)
    session.commit()
    print app.url_map
    app.run(host='0.0.0.0',port=8080)



