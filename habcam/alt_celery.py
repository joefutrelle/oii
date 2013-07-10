import logging
import sys

from celery import Celery

from skimage import img_as_float
from skimage.io import imread

from oii.config import get_config
from oii.psql import xa
from oii.resolver import parse_stream

from oii.habcam.lightfield.altitude import stereo2altitude

MODULE='oii.habcam.alt_celery'

#celery = Celery(MODULE)

logger = logging.getLogger(MODULE)

# example config file
# resolver = /some/path/to/a/resolver.xml
# psql_connect = host=blah user=blah password=foo dbname=quux

def alt_exists(imagename,psql_connect):
    """ check if the database has a parallax alt record for this image """
    with xa(psql_connect) as c,db:
        db.execute('select count(*) from parallax where imagename=%s',(imagename,))
        count = db.fetchall()[0][0]
        return count != 0

def write_alt(imagename,alt,x,y,psql_connect):
    """ given an imagename and alt, write it to the database (if it doesn't already exist) """
    with xa(psql_connect) as c,db:
        db.execute('select count(*) from parallax where imagename=%s',(imagename,))
        count = db.fetchall()[0][0]
        if count == 0:
            db.execute('insert into parallax (imagename,parallax_alt,x,y) values (%s,%s,%s,%s)',(imagename,alt,x,y))
            c.commit()
            logging.info('DONE %s %.3f' % (imagename,alt))

def compute_alt(cfa_LR_path):
    """ given the path to a RAW 16-bit 1stereo pair, compute the altitude """
    cfa_LR = img_as_float(imread(cfa_LR_path,plugin='freeimage'))
    x,y,alt = stereo2altitude(cfa_LR)
    return x,y,alt

def alt_bin(bin_lid,resolver,psql_connect):
    R = parse_stream(resolver)
    for hit in R['list_images'].resolve_all(pid=bin_lid):
        (imagename, cfa_LR_path) = hit.lid, hit.p
        x,y,alt = compute_alt(cfa_LR_path)
        print '%s %d %d %.3f' % (imagename,x,y,alt)

if __name__=='__main__':
    bin_lid = sys.argv[1]
    alt_bin(bin_lid,'mrf_noaa.xml',None)
