from oii.utils import dict_slice
from oii.annotation.storage import AnnotationStore
import psycopg2 as psql

class PsqlAnnotationStore(AnnotationStore):
    # name, type, unique
    SCHEMA = [
        ('pid', 'text', True),
        ('image', 'text', False),
        ('category', 'text', False),
        ('annotator', 'text', False),
        ('timestamp', 'timestamp with time zone', False)
    ]
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect
    @property
    def FIELDS(self):
        return zip(*self.SCHEMA)[0]
    def create(self):
        c = psql.connect(self.psql_connect)
        db = c.cursor()
        db.execute('drop table annotations')
        db.execute('create table annotations (%s)' % (', '.join([n+' '+t for n,t,_ in self.SCHEMA])))
        for n,_,u in self.SCHEMA:
            if u:
                uq = 'unique '
            else:
                uq = ''
            db.execute('create %sindex ix_ann_%s on annotations (%s)' % (uq,n,n))
        c.commit()
    def list_annotations(self,**template):
        # convert template (e.g., {'pid': 'foo', 'image': 'bar'}
        # to where clause and values, e.g.,
        # 'pid=%s and image=%s',('foo','bar')
        FIELDS = self.FIELDS
        wc = [(k+'=%s',v) for k,v in template.items() if k in FIELDS]
        (where,values) = (' and '.join(zip(*wc)[0]), zip(*wc)[1])
        query = 'select %s from annotations where %s' % (', '.join(FIELDS), where)
        c = psql.connect(self.psql_connect)
        db = c.cursor()
        db.execute(query,values)
        while True:
            rows = db.fetchmany()
            for row in rows:
                yield dict(zip(FIELDS,row))
            if len(rows) == 0:
                break
    def fetch_annotation(self,annotation_pid):
        for ann in self.list_annotations(pid=annotation_pid):
            return ann
    def create_annotations(self,annotations):
        FIELDS = self.FIELDS
        c = psql.connect(self.psql_connect)
        db = c.cursor()
        for ann in annotations:
            record = dict(zip(FIELDS,[None for _ in range(len(FIELDS))]))
            record.update(dict_slice(ann,FIELDS))
            query = 'insert into annotations (%s) values (%s)' % (', '.join(FIELDS), ', '.join(['%s' for _ in range(len(FIELDS))]))
            db.execute(query,[record[k] for k in FIELDS])
        c.commit()
            
store = PsqlAnnotationStore('dbname=ifcb user=jfutrelle password=vNLH814i')
store.create()
store.list_annotations(image='fish',annotator='cow',pid='zazz')

ann = dict(pid='foo', image='bar')
ann2 = dict(pid='baz', image='sniz', annotator='quux')
ann3 = dict(pid='fnord', image='bar', annotator='quux')
store.create_annotations([ann, ann2, ann3])

print store.fetch_annotation('foo')
for ann in store.list_annotations(annotator='quux'):
    print ann
            