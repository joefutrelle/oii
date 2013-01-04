import psycopg2 as psql
from psycopg2.extras import RealDictCursor
from oii.psql import xa
import json
import re

DEC2FLOAT = psql.extensions.new_type(
    psql.extensions.DECIMAL.values,
    'DEC2FLOAT',
    lambda value, curs: float(value) if value is not None else None)
psql.extensions.register_type(DEC2FLOAT)

class Metadata(object):
    def __init__(self,config):
        self.psql_connect = config.psql_connect
    def json(self,imagename):
        imagename = re.sub(r'\.[a-z]+$','',imagename)
        with xa(self.psql_connect) as (c,_):
            db = c.cursor(cursor_factory=RealDictCursor)
            db.execute('select * from web_service_image_metadata where imagename like %s',(imagename+'%',))
            return json.dumps(db.fetchone())

import sys

class Derp(object):
    pass

if __name__=='__main__':
    (u,p) = (sys.argv[1], sys.argv[2])
    psql_connect = 'host=molamola.whoi.edu user=%s password=%s dbname=habcam_v3' % (u,p)
    config = Derp()
    config.psql_connect = psql_connect
    with xa(psql_connect) as (c,db):
        db.execute('select imagename from web_service_image_metadata order by random() limit 1')
        for row in db.fetchall():
            imagename = row[0]
    print 'imagename = %s' % imagename
    metadata = Metadata(config)
    print metadata.json(imagename)
