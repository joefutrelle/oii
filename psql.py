import psycopg2 as psql
from oii.utils import dict_slice

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

def exists(db,query,params=()):
    db.execute('select exists (%s)' % query,params)
    return db.fetchone()[0]

# simplest ORM ever
class PsqlStore(object):
    def __init__(self,psql_connect):
        self.psql_connect = psql_connect
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
                self.create_indexes(self.FIELDS,c)
            c.commit()
    def create_indexes(self,fields=None,connection=None):
        if fields is None:
            fields = self.FIELDS
        if connection is None:
            c = psql.connect(self.psql_connect)
        else:
            c = connection
        db = c.cursor()
        for n,_,u in self.SCHEMA:
            if n in fields:
                if u:
                    uq = 'unique '
                else:
                    uq = ''
                print 'create %sindex ix_%s_%s on %s (%s)' % (uq,self.TABLE_NAME,n,self.TABLE_NAME,n)
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
        if len(wc) > 0:
            (where,values) = (' and '.join(zip(*wc)[0]), zip(*wc)[1])
            query = 'select %s from %s where %s' % (', '.join(FIELDS), self.TABLE_NAME, where)
        else: # list all
            query = 'select %s from %s' % (', '.join(FIELDS), self.TABLE_NAME)
            values = None
        with xa(self.psql_connect) as (_,db):
            db.execute(query,values)
            for row in iterrows(db,FIELDS):
                yield self.parse_row(row)
