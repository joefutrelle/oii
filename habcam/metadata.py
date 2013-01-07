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
    def image(self,imagename):
        imagename = re.sub(r'\.[a-z]+$','',imagename)
        with xa(self.psql_connect) as (c,_):
            db = c.cursor(cursor_factory=RealDictCursor)
            db.execute('select * from web_service_image_metadata where imagename like %s',(imagename+'%',))
            return db.fetchone()
    def bin(self,bin_lid):
        """bin lid is lid of 10-minute bin (e.g., 201203.20120623.1220)"""
        pattern = re.sub(r'\d$','',bin_lid) + '%'
        print pattern
        with xa(self.psql_connect) as (c,_):
            db = c.cursor(cursor_factory=RealDictCursor)
            db.execute('select * from web_service_image_metadata where imagename like %s',(bin_lid+'%',))
            return db.fetchall()
    def json(self,imagename):
        return json.dumps(self.image(imagename))
    def json_bin(self,bin_lid):
        """bin lid is lid of 10-minute bin (e.g., 201203.20120623.1220)"""
        return json.dumps(self.bin(bin_lid))

import sys

class Derp(object):
    pass

if __name__=='__main__':
    (u,p) = (sys.argv[1], sys.argv[2])
    psql_connect = 'host=molamola.whoi.edu user=%s password=%s dbname=habcam_v3' % (u,p)
    config = Derp()
    config.psql_connect = psql_connect
    metadata = Metadata(config)
    with xa(psql_connect) as (c,db):
        db.execute('select imagename from web_service_image_metadata order by random() limit 1')
        for row in db.fetchall():
            imagename = row[0]
    print 'imagename = %s' % imagename
    bin_lid = re.sub(r'\d{5}\.\d+\.[a-zA-Z][a-zA-Z0-9]+$','',imagename)
    print 'bin_lid = %s' % bin_lid
    print metadata.json_bin(bin_lid)

