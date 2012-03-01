from oii.utils import dict_slice
from oii.annotation.storage import AnnotationStore
from oii.annotation.assignments import AssignmentStore
import psycopg2 as psql
from unittest import TestCase
from tempfile import NamedTemporaryFile
import os

# transaction class to use with "with". give it connection params
# and it returns the connection and a cursor.
class xa(object):
    def __init__(self,connect_params):
        self.connect_params = connect_params
    def __enter__(self):
        self.c = psql.connect(self.connect_params)
        db = self.c.cursor()
        return (self.c,db)
    def __exit__(self, type, value, traceback):
        self.c.close()

# iterate over rows. uses fetchmany() to reduce memory load
def iterrows(cursor,columns):
    while True:
        rows = cursor.fetchmany()
        for row in rows:
            yield dict(zip(columns,row))
        if len(rows) == 0:
            break
        
# simplest ORM ever
class PsqlStore(object):
    @property
    def FIELDS(self):
        return zip(*self.SCHEMA)[0]
    def create(self,indexes=True):
        with xa(self.psql_connect) as (c,db):
            try:
                db.execute('drop table %s' % self.TABLE_NAME)
            except:
                c.rollback()
            db.execute('create table %s (%s)' % (self.TABLE_NAME,', '.join([n+' '+t for n,t,_ in self.SCHEMA])))
            if indexes:
                self.create_indexes(c)
            c.commit()
    def create_indexes(self,connection=None):
        if connection is None:
            c = psql.connect(self.psql_connect)
        else:
            c = connection
        db = c.cursor()
        for n,_,u in self.SCHEMA:
            if u:
                uq = 'unique '
            else:
                uq = ''
            db.execute('create %sindex ix_%s_%s on %s (%s)' % (uq,self.TABLE_NAME,n,self.TABLE_NAME,n))
        if connection is None:
            c.commit()
    def parse_row(self,row):
        # convert a row (represented as a column/value dict) to a record
        return row
    def unparse_row(self,record):
        # convert an object to a row
        # default is simply columns named after fields, with SQL NULL (Python None) for any missing values
        FIELDS = self.FIELDS
        row = dict(zip(FIELDS,[None for _ in range(len(FIELDS))]))
        row.update(dict_slice(record,FIELDS))
        return row
    def insert(self,records):
        with xa(self.psql_connect) as (c,db):
            for record in records:
                row = self.unparse_row(record)
                columns = row.keys()
                query = 'insert into %s (%s) values (%s)' % (self.TABLE_NAME,', '.join(columns), ', '.join(['%s' for _ in range(len(columns))]))
                db.execute(query,[row[k] for k in columns])
            c.commit()
    def query(self,**template):
        # convert template (e.g., {'pid': 'foo', 'image': 'bar'}
        # to where clause and values, e.g.,
        # 'pid=%s and image=%s',('foo','bar')
        FIELDS = self.FIELDS
        wc = [(k+'=%s',v) for k,v in template.items() if k in FIELDS]
        (where,values) = (' and '.join(zip(*wc)[0]), zip(*wc)[1])
        query = 'select %s from %s where %s' % (', '.join(FIELDS), self.TABLE_NAME, where)
        with xa(self.psql_connect) as (_,db):
            db.execute(query,values)
            for row in iterrows(db,FIELDS):
                yield self.parse_row(row)
    
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
                record = dict(zip(FIELDS,[None for _ in range(len(FIELDS))]))
                record.update(dict_slice(ann,FIELDS))
                tmp.write(','.join([record[f] for f in FIELDS]) + '\n')
            tmp.flush()
            name = tmp.name
        os.chmod(name, 0777)
        c = psql.connect(self.psql_connect)
        db = c.cursor()
        db.execute('copy annotations from \'%s\' with csv header' % name)
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
        store = PsqlAssignmentStore('dbname=ifcb user=jfutrelle password=xxx')
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
        store = PsqlAnnotationStore('dbname=ifcb user=jfutrelle password=xxxx')
        store.create()
        store.list_annotations(image='fish',annotator='cow',pid='zazz')
        ann = dict(pid='foo', image='bar')
        ann2 = dict(pid='baz', image='sniz', annotator='quux')
        ann3 = dict(pid='fnord', image='bar', annotator='quux')
        store.create_annotations([ann, ann2, ann3])
        assert store.fetch_annotation('foo') == dict(category=None, timestamp=None, image='bar', pid='foo', annotator=None)
        (o,t) = list(store.list_annotations(annotator='quux'))
        assert o == dict(category=None, timestamp=None, image='sniz', pid='baz', annotator='quux')
        assert t == dict(category=None, timestamp=None, image='bar', pid='fnord', annotator='quux')

