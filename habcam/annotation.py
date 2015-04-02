from oii.annotation.storage import AnnotationStore
from oii.psql import xa
import json
import psycopg2 as psql
from oii.utils import dict_slice

# map json struct names to db column names
# if either change, this needs to be changed ...
json2db = {
"image": "image_id",
"scope": "scope_id",
"category": "category_id",
"geometry": "geometry_text",
"annotator": "annotator_id",
"timestamp": "timestamp",
"assignment": "assignment_id",
"pid": "annotation_id",
"deprecated" : "deprecated",
"percent_cover" : "percent_cover"
}
SELECT_CLAUSE = "select image_id, scope_id, category_id, geometry_text, annotator_id, to_char(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"hh:MI:ss\"Z\"') as timestamp, assignment_id, annotation_id, deprecated, percent_cover from annotations "

# abstract API for storing, querying, and creating annotations
class HabcamAnnotationStore(AnnotationStore):
    def __init__(self,config):
        self.config = config
    def __db(self): # FIXME is this unused?
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        return (connection, cursor)
    def __consume(self,cursor):
        for row in cursor.fetchall():
            d = {}
            d['image'] = row[0]
            d['scope'] = row[1]
            d['category'] = row[2]
            d['geometry'] = json.loads('{'+row[3]+'}')
            d['annotator'] = row[4]
            d['timestamp'] = row[5]
            d['assignment'] = row[6]
            d['pid'] = row[7]
	    d['deprecated'] = row[8]
            d['percent_cover'] = row[9]
            yield d
    def list_annotations(self,**template):
        "List annotations which match the given template (flat dictionary, k/v's in template must match k/v's in candidate"
        where_clauses = []
        where_values = []
        for k,v in template.items():	
            where_clauses.append(json2db[k]+'~*imageid_repl(%s)')
            where_values.append(v)
        with xa(self.config.psql_connect) as (connection,cursor):
            if(len(where_clauses) > 0):
               cursor.execute(SELECT_CLAUSE +  'where ' + 'and '.join(where_clauses), tuple(where_values))
            else:
                cursor.execute(SELECT_CLAUSE)
            return [ann for ann in self.__consume(cursor)]
    def fetch_annotation(self,pid):
        "Fetch an annotation by its PID"
        pd = dict(pid=pid)
        for ann in self.list_annotations(**pd):
            return ann
    def deprecate_annotation(self,pid):
	"Deprecate an annotation given the pid"
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('update annotations set deprecated = true where annotation_id = %s',(pid,))
            connection.commit()
        return self.fetch_annotation(pid)
    def create_annotations(self,annotations):
        tuples = []
        for d in annotations:
            fields = 'image,scope,category,geometry,annotator,timestamp,assignment,pid,percent_cover'
            d = dict_slice(d,fields,None)
            tuples.append((d['image'], d['scope'], d['category'], json.dumps(d['geometry']).strip('{}'), d['annotator'],d['timestamp'], d['assignment'], d['pid'], d['percent_cover']))
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.executemany("insert into annotations (image_id, scope_id, category_id, geometry_text, annotator_id, timestamp, assignment_id, annotation_id, percent_cover) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)", tuples)
            connection.commit()
