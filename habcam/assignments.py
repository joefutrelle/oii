import psycopg2 as psql
from oii.config import get_config
import re
from oii.annotation.assignments import AssignmentStore
from oii.psql import xa

class HabcamAssignmentStore(AssignmentStore):
    def __init__(self,config):
        self.config = config
        self.assignment_fields = ['assignment_id','idmode_id','site_description','project_name','priority','initials','date','num_images','comment']
	self.idmode_fields = ['idmode_id','idmode_name'];
    def lid(self,pid,namespace=None):
        return re.sub('.*/','',pid)
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
        d['mode'] = d['idmode_id']
        d['label'] = '%s: %s @ %s' % (str(d['assignment_id']), d['project_name'], d['site_description'])
        return d
    def __row2idmode(self,row):
        d = dict(zip(self.idmode_fields, row))
	#d['pid'] = d['idmode_id'];
        #d['label'] = d['idmode_name']
        return d
    def list_assignments(self):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select %s from assignments ORDER BY assignment_id desc' % (','.join(self.assignment_fields)))
            for row in cursor.fetchall():
                yield self.__row2assignment(row)
    def list_idmodes(self):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select distinct idmode_id,idmode_name from idmodes where idmode_name is not null order by idmode_id')
            for row in cursor.fetchall():
                yield self.__row2idmode(row)
    def fetch_assignment(self,pid):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select '+(','.join(self.assignment_fields))+' from assignments where assignment_id=%s', (self.lid(pid),))
            for row in cursor.fetchall():
                row = self.__row2assignment(row)
                row['images'] = self.pid(row['assignment_id'])
                return row
    def list_images(self,pid,limit=None,offset=0,status=None):
        with xa(self.config.psql_connect) as (connection,cursor):
            params = [self.lid(pid)]
            if status is None:
                status_clause = ''
            else:
                status_clause = 'and status = %s'
                params += [status]
            if limit is None:
                limitclause = ''
            else:
                limitclause = 'limit %s '
                params += [limit]
            params += [offset]
            cursor.execute('select imagename from imagelist where assignment_id=%s '+status_clause+' order by imagename '+limitclause+'offset %s', tuple(params))
            for row in cursor.fetchall():
                d = {}
                d['pid'] = self.pid(row[0], self.config.image_namespace)
                d['image'] = d['pid']
                yield d
    def find_image(self,pid,offset,status,post_status=None):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select imagename,status from imagelist where assignment_id=%s order by imagename offset %s for update of imagelist',(self.lid(pid),offset))
            i = offset
            for row in cursor.fetchall():
                if row[1]==status:
                    if post_status is not None:
                        cursor.execute('update imagelist set status=%s where assignment_id=%s and imagename=%s',(post_status,self.lid(pid),row[0]))
                        connection.commit()
                    return i+1
                i += 1
            return offset
    def set_status(self,assignment_id,image_id,status):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        print 'gonna set status to %s for assignment %s image %s' % (status,self.lid(assignment_id),self.lid(image_id))
        cursor.execute('update imagelist set status=%s where assignment_id=%s and imagename=%s',(status,int(self.lid(assignment_id)),self.lid(image_id)))
        connection.commit()

if __name__=='__main__':
    config = get_config('habcam_annotation.conf')
    has = HabcamAssignmentStore(config)
    for ass in has.list_assignments():
        print ass
