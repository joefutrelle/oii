import psycopg2 as psql
from oii.config import get_config
import re
from oii.annotation.assignments import AssignmentStore

class HabcamAssignmentStore(AssignmentStore):
    def __init__(self,config):
        self.config = config
        self.assignment_fields = ['assignment_id','idmode','site_description','project_name','priority','initials','date']
    def lid(self,pid,namespace=None):
        if namespace is None:
            namespace = self.config.namespace
        if namespace is None:
            return pid
        return re.sub(namespace,'',pid)
    def pid(self,lid,namespace=None):
        if namespace is None:
            namespace = self.config.namespace
        if namespace is None:
            return str(lid)
        else:
            return namespace + str(lid)
    def __row2assignment(self,row):
        d = dict(zip(self.assignment_fields, row))
        try:
            d['pid'] = self.pid(d['assignment_id'])
        except KeyError:
            pass
        try:
            d['images'] = self.pid(d['imagelist'])
        except KeyError:
            pass
        d['mode'] = d['idmode']
        d['label'] = '%s: %s @ %s' % (str(d['assignment_id']), d['project_name'], d['site_description'])
        return d
    def list_assignments(self):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        cursor.execute('select %s from assignments' % (','.join(self.assignment_fields)))
        for row in cursor.fetchall():
            yield self.__row2assignment(row)
    def fetch_assignment(self,pid):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        cursor.execute('select '+(','.join(self.assignment_fields))+' from assignments where assignment_id=%s', (self.lid(pid),))
        for row in cursor.fetchall():
            row = self.__row2assignment(row)
            row['images'] = self.pid(row['assignment_id'])
            return row
    def list_images(self,pid,limit=None,offset=0):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        if limit is None:
            limitclause = ''
        else:
            limitclause = 'limit %d ' % limit
        cursor.execute('select imagename from imagelist where assignment_id=%s order by imagename '+limitclause+'offset %s', (self.lid(pid),offset))
        for row in cursor.fetchall():
            d = {}
            d['pid'] = self.pid(row[0], self.config.image_namespace)
            d['image'] = d['pid']
            yield d

if __name__=='__main__':
    config = get_config('habcam_annotation.conf')
    has = HabcamAssignmentStore(config)
    for ass in has.list_assignments():
        print ass