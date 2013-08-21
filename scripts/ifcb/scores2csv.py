import os
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
outdir = config.outdir

psql_connect = '%s dbname=%s' % (config.psql_connect, config.dbname)

R = parse_stream(config.resolver)

NAMESPACE='http://demi.whoi.edu/mvco/'

feed = IfcbFeed(psql_connect)

start=strptime('2005-01-01T00:00:00Z',ISO_8601_FORMAT);
end=strptime('2014-01-01T00:00:00Z',ISO_8601_FORMAT);

with xa(psql_connect) as (c, db):
    bin_lids = list(feed.between(start,end))

N=8
pids = []
for n in range(N):
    pid = os.fork()
    if pid == 0:
        outfile = os.path.join(outdir,'scores_%d.csv' % n)
        with open(outfile,'w') as of:
            for bin_lid in bin_lids[n::N]:
                bin_pid = NAMESPACE + bin_lid
                print bin_pid

                hit = R['class_scores'].resolve(pid=bin_pid)
                if hit is not None:
                    class_mat = load_class_scores(hit.value)

                    for roinum, label, score in class_scores_mat2class_label_score(class_mat):
                        print >> of, '%s,%s,%d,%.2f' % (bin_lid,label,roinum,score)
        os._exit(0)
    else:
        pids += [pid]
for pid in pids:
    os.waitpid(pid,0)
