import sys

from time import strptime

import psycopg2

from oii.psql import xa
from oii.config import get_config
from oii.ifcb.classification import class_scores_mat2class_label_score, load_class_scores
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

start=strptime('2005-01-01T00:00:00Z',ISO_8601_FORMAT);
end=strptime('2014-01-01T00:00:00Z',ISO_8601_FORMAT);

s = 'select count(*) from autoclass where bin_lid=%s'
q = 'insert into autoclass (bin_lid, class_label, roinums, scores) values (%s, %s, %s, %s)'

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

                roinums = {}
                scores = {}
                for roinum, label, score in class_scores_mat2class_label_score(class_mat):
                    if not label in roinums:
                        roinums[label] = []
                        scores[label] = []
                    roinums[label] = roinums[label] + [roinum]
                    scores[label] = scores[label] + [score]
            
                for label in roinums.keys():
                    db.execute(q,(bin_lid,label,roinums[label],scores[label]))

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
