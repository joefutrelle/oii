from oii.psql import PsqlStore, xa, iterrows
from oii.utils import dict_slice
from oii.annotation.storage import AnnotationStore
from oii.annotation.assignments import AssignmentStore
import psycopg2 as psql
from unittest import TestCase
from tempfile import NamedTemporaryFile
import os

class PsqlAnnotationStore(AnnotationStore,PsqlStore):
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect
        self.TABLE_NAME = 'annotations'
        # name, type, unique
        self.SCHEMA = [
          ('pid', 'text', True),
          ('image', 'text', False),
          ('category', 'text', False),
          ('annotator', 'text', False),
          ('assignment', 'text', False),
          ('timestamp', 'timestamp with time zone', False)
       ]
    @property
    def FIELDS(self):
        return zip(*self.SCHEMA)[0]
    def list_annotations(self,**template):
        return self.query(**template)
    def fetch_annotation(self,annotation_pid):
        for ann in self.list_annotations(pid=annotation_pid):
            return ann
    def create_annotations(self,annotations):
        self.insert(annotations)
    def bulk_create_annotations(self,annotations):
        FIELDS = self.FIELDS
        with NamedTemporaryFile(dir='/tmp',delete=False) as tmp:
            tmp.write(','.join(FIELDS)+'\n')
            for ann in annotations:
                record = dict(zip(FIELDS,['NULL' for _ in range(len(FIELDS))]))
                record.update(dict_slice(ann,FIELDS))
                tmp.write(','.join([record[f] for f in FIELDS]) + '\n')
            tmp.flush()
            name = tmp.name
        os.chmod(name, 0777)
        c = psql.connect(self.psql_connect)
        db = c.cursor()
        db.execute('copy annotations from \'%s\' with null as \'NULL\' csv header' % name)
        c.commit()
        os.remove(name)

class PsqlAssignmentStore(AssignmentStore,PsqlStore):
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect
        self.TABLE_NAME = 'assignments'
        # name, type, unique
        self.SCHEMA = [
          ('pid', 'text', True),
          ('label', 'text', False),
          ('annotator', 'text', False),
          ('updated', 'timestamp with time zone', False),
          ('status', 'text', False),
          ('images', 'text[]', False)
        ]
    def parse_row(self,row):
        row['images'] = [dict(pid=pid, image=pid+'.jpg') for pid in row['images']]
        return row
    def unparse_row(self,record):
        record = record.copy()
        record['images'] = [i['pid'] for i in record['images']]
        return record
    def list_assignments(self):
        with xa(self.psql_connect) as (_,db):
            db.execute('select * from %s' % self.TABLE_NAME)
            for row in iterrows(db,self.FIELDS):
                yield self.parse_row(row)

class TestPsqlAssignmentStore(TestCase):
    def test_stuff(self):
        store = PsqlAssignmentStore('dbname=ifcb user=jfutrelle password=vNLH814i')
        store.create()
        assignments = [{
            "pid": "http://foo.bar/assignments/baz",
            "label": "Identify quux for images from fnord cruise",
            "annotator": "Ann O. Tator",
            "status": "new",
            "images": [{
                 "pid": "http://foo.bar/images/abcdef",
                 "image": "http://foo.bar/images/abcdef.jpg"
            }]
        }]
        store.insert(assignments)
        for assn in store.list_assignments():
            print assn
                        
# tests
class TestPsqlAnnotationStore(TestCase):
    def test_stuff(self):
        store = PsqlAnnotationStore('dbname=ifcb user=jfutrelle password=vNLH814i')
        store.create()
        store.list_annotations(image='fish',annotator='cow',pid='zazz')
        ann = dict(pid='foo', image='bar')
        ann2 = dict(pid='baz', image='sniz', annotator='quux')
        ann3 = dict(pid='fnord', image='bar', annotator='quux')
        store.create_annotations([ann, ann2, ann3])
        assert store.fetch_annotation('foo') == dict(assignment=None, category=None, timestamp=None, image='bar', pid='foo', annotator=None)
        (o,t) = list(store.list_annotations(annotator='quux'))
        assert o == dict(assignment=None, category=None, timestamp=None, image='sniz', pid='baz', annotator='quux')
        assert t == dict(assignment=None, category=None, timestamp=None, image='bar', pid='fnord', annotator='quux')

