# import manual annotations
# expected fields:
# 1. bin lid (ignore any extension e.g., .mat)
# 2. roi number
# 3. class label
# 4. annotator lid (e.g., EBrownlee)
import os
import csv
from oii.annotation.ifcb import DATA_NAMESPACE, ANNOTATION_NAMESPACE, PERSON_NAMESPACE
from oii.utils import gen_id
from oii.annotation import PID, TIMESTAMP, ANNOTATOR, IMAGE, CATEGORY
from oii.times import iso8601
from oii.annotation.psql import PsqlAnnotationStore
import sys

MOUNT_POINT = '/Volumes/d_work'
DATA_DIR = os.path.join(MOUNT_POINT,'IFCB1','ifcb_data_mvco_jun06','Manual_fromClass','annotations_csv')

def annotations_for(file):
    for raw in csv.DictReader(fin,['bin','roi','category','annotator']):
        yield {
            PID: gen_id(ANNOTATION_NAMESPACE),
            IMAGE: DATA_NAMESPACE + raw['bin'].replace('.mat','_') + raw['roi'],
            TIMESTAMP: iso8601(),
            CATEGORY: raw['category'],
            ANNOTATOR: raw['annotator'],
        }

store = PsqlAnnotationStore(sys.argv[1]) # arg must be full psql connect string dbname=xxx user=xxx password=xxx
print 'initializing store...'
store.create(False)
for file in os.listdir(DATA_DIR):
    with open(os.path.join(DATA_DIR,file),'r') as fin:
        anns = list(annotations_for(fin))
        store.bulk_create_annotations(anns)
        now = iso8601()
        print '%s created %d annotation(s) for %s' % (now, len(anns), file)
print 'creating indexes ... this will take a long time'
store.create_indexes()
            