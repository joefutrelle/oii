from oii.annotation.storage import AnnotationStore
import json
import psycopg2 as psql

# map json struct names to db column names
# if either change, this needs to be changed ...
json2db = {
"image": "image_id",
"category": "category_id",
"geometry": "geometry_text",
"annotator": "annotator_id",
"timestamp": "timestamp",
"assignment": "assignment_id",
"pid": "annotation_id"
}
SELECT_CLAUSE = "select image_id, category_id, geometry_text, annotator_id, 'timestamp', assignment_id, annotation_id from raw_annotations "

# abstract API for storing, querying, and creating annotations
class HabcamAnnotationStore(AnnotationStore):
    def __init__(self,config):
        self.config = config
    def __db(self):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        return (connection, cursor)
    def __consume(self,cursor):
        for row in cursor.fetchall():
            d = {}
            d['image'] = row[0]
            d['category'] = row[1]
            d['geometry'] = json.loads(row[2])
            d['annotator'] = row[3]
            d['timestamp'] = row[4]
            d['assignment'] = row[5]
            d['pid'] = row[6]
            yield d
    def list_annotations(self,**template):
        "List annotations which match the given template (flat dictionary, k/v's in template must match k/v's in candidate"
        where_clauses = []
        where_values = []
        for k,v in template.items():
            where_clauses.append(json2db[k]+'=%s')
            where_values.append(v)
        (connection, cursor) = self.__db()
        if(len(where_clauses) > 0):
            cursor.execute(SELECT_CLAUSE +  'where ' + 'and '.join(where_clauses), tuple(where_values))
        else:
            cursor.execute(SELECT_CLAUSE)
        for ann in self.__consume(cursor):
            yield ann
    def fetch_annotation(self,pid):
        "Fetch an annotation by its PID"
        for ann in list_annotations(dict(pid=pid)):
            return ann
    def create_annotations(self,annotations):
        tuples = []
        for d in annotations:
            tuples.append((d['image'], d['category'], json.dumps(d['geometry']), d['annotator'],d['timestamp'], d['assignment'], d['pid']))
        (connection, cursor) = self.__db()
        cursor.executemany("insert into raw_annotations (image_id, category_id, geometry_text, annotator_id, timestamp, assignment_id, annotation_id) values (%s,%s,%s,%s,%s,%s,%s)", tuples)
