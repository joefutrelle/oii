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

celery = Celery(MODULE)

logger = logging.getLogger(MODULE)

# example config file
# resolver = /some/path/to/a/resolver.xml
# psql_connect = host=blah user=blah password=foo dbname=quux

def alt_exists(imagename,psql_connect):
    """ check if the database has a parallax alt record for this image """
    with xa(psql_connect) as (c,db):
        db.execute('select count(*) from parallax where imagename=%s',(imagename,))
        count = db.fetchall()[0][0]
        return count != 0

def write_alt(imagename,alt,x,y,psql_connect):
    """ given an imagename and alt, write it to the database (if it doesn't already exist) """
    with xa(psql_connect) as (c,db):
        db.execute('select count(*) from parallax where imagename=%s',(imagename,))
        count = db.fetchall()[0][0]
        if count == 0:
            db.execute('insert into parallax (imagename,parallax_alt,x,y) values (%s,%s,%s,%s)',(imagename,alt,x,y))
            c.commit()
            logging.info('WROTE %s %d %d %.3f' % (imagename,x,y,alt))

def compute_alt(cfa_LR_path):
    """ given the path to a RAW 16-bit 1stereo pair, compute the altitude """
    cfa_LR = img_as_float(imread(cfa_LR_path,plugin='freeimage'))
    x,y,alt = stereo2altitude(cfa_LR)
    return x,y,alt

def alt_bin(bin_lid,resolver,psql_connect):
    R = parse_stream(resolver)
    # 'list images' should return:
    # - lid: imagename (e.g., 201303.20130621.1723.134329.55432.tif')
    # - p: full path to RAW 16-bit side-by-side stereo TIFF
    skip = 0
    for hit in R['list_images'].resolve_all(pid=bin_lid):
        (imagename, cfa_LR_path) = hit.lid, hit.p
        if not alt_exists(imagename,psql_connect):
            if skip > 0:
                logging.info('SKIPPED %d image(s)' % skip)
                skip = 0
            logging.info('START %s' % imagename)
            x,y,alt = compute_alt(cfa_LR_path)
            if x != 0 or y != 0:
                write_alt(imagename,alt,x,y,psql_connect)
        else:
            skip += 1

@celery.task
def do_alt(imagename,cfa_LR_path,psql_connect):
    if not alt_exists(imagename,psql_connect):
        logging.info('START %s' % imagename)
        x,y,alt = compute_alt(cfa_LR_path)
        if x != 0 or y != 0:
            write_alt(imagename,alt,x,y,psql_connect)
    else:
        logging.info('SKIPPED %s' % imagename)

@celery.task
def queue_bin(bin_lid,config):
    config = get_config('alt_celery.conf')
    R = parse_stream(config.resolver)
    psql_connect = config.psql_connect
    for hit in R['list_images'].resolve_all(pid=bin_lid):
        (imagename, cfa_LR_path) = hit.lid, hit.p
        do_alt.s(imagename, cfa_LR_path, psql_connect).apply_async(queue='alt') # FIXME hardcoded queue name

# when running this as a worker use a queue name like leg1_alt
# and set concurrency to number of hardware threads
# so:
# celery -A oii.habcam.alt_celery worker -c 24 --queue=leg1_alt

# to enqueue all images from bin do this:
#
# celery --config={celery config file} call oii.habcam.alt_celery.queue_bin --args='["{bin lid}" "{alt config file}"]' --queue=leg1_alt


if __name__=='__main__':
    config = get_config('alt_celery.conf')
    R = parse_stream(config.resolver)
    psql_connect = config.psql_connect
    with xa(psql_connect) as (c,db):
        db.execute("""
select imageid || '.tif'
from burton_alts
where parallax_alt is null
""")
        while True:
            rows = db.fetchmany(100)
            if len(rows) == 0:
                break
            else:
                for row in rows:
                    imagename = row[0]
                    hit = R['cfa_LR'].resolve(pid=imagename)
                    if hit is not None:
                        cfa_LR_path = hit.value
                        print 'queueing %s %s' % (imagename, cfa_LR_path)
                        do_alt.s(imagename, cfa_LR_path, psql_connect).apply_async(queue='alt') # FIXME hardcoded queue name

