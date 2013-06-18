import sys

from time import strptime

import psycopg2

from oii.psql import xa
from oii.config import get_config
from oii.ifcb.classification import class_scores_mat2class_labels, load_class_scores
from oii.resolver import parse_stream
from oii.ifcb.db import IfcbFeed
from oii.times import text2utcdatetime, ISO_8601_FORMAT

try:
    time_series = sys.argv[1]
except:
    time_series = 'mvco'

config = get_config('./db.conf',time_series)

psql_connect = '%s dbname=%s' % (config.psql_connect, config.dbname)

R = parse_stream(config.resolver)

NAMESPACE='http://demi.whoi.edu/mvco/'

feed = IfcbFeed(psql_connect)

start=strptime('2012-01-01T00:00:00Z',ISO_8601_FORMAT);
end=strptime('2013-01-01T00:00:00Z',ISO_8601_FORMAT);

s = 'select count(*) from autoclass where bin_lid=%s'
q = 'insert into autoclass (bin_lid, class_label, roinums) values (%s, %s, %s)'

with xa(psql_connect) as (c, db):
    n = 0
    for bin_lid in feed.between(start,end):
        bin_pid = NAMESPACE + bin_lid

        db.execute(s,(bin_lid,))
        count = db.fetchone()[0]
        if count == 0:
            print 'indexing %s' % bin_pid
            hit = R['class_scores'].resolve(pid=bin_pid)
            if hit is not None:
                class_mat = load_class_scores(hit.value)

                index = {}
                for roinum, label in class_scores_mat2class_labels(class_mat, threshold=0.0):
                    if not label in index:
                        index[label] = []
                    index[label] = index[label] + [roinum]
            
                for label in index.keys():
                    db.execute(q,(bin_lid,label,index[label]))

                n += 1
                if n > 100:
                    print 'committing ...'
                    c.commit()
                    print 'done'
                    n = 0
        else:
            print 'skipping %s' % bin_pid
            
    print 'committing ...'
    c.commit()
    print 'done'
