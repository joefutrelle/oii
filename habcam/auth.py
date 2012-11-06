import sys
import traceback
from oii.psql import xa
from oii.webapi.auth_callbacks import PsqlAuthentication
from oii.utils import gen_id, md5_string
from oii.config import get_config

class HabcamAuthentication(PsqlAuthentication):
    def __init__(self,config):
        super(HabcamAuthentication,self).__init__(config,"select * from auth where annotator_id=%s and passwd=md5(salt || %s)")
    def add_user(self,username, password, **kvs):
        salt = gen_id() # generate salt
        kvs['annotator_id'] = username
        kvs['passwd'] = md5_string(salt + password) # md5 salt + password is the encrypted credential
        kvs['salt'] = salt
        kvs = kvs.items()
        ks = ','.join([k for k,_ in kvs])
        ss = ','.join(['%s' for _ in kvs])
        vs = [v for _,v in kvs]
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('insert into auth (' + ks + ') values (' + ss + ')',vs)
            connection.commit()
    def delete_user(self,username):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('delete from auth where annotator_id = %s',(username,))
            connection.commit()
    def list_users(self):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select * from auth')
            return list(cursor.fetchall())

if __name__=='__main__':
    try:
        config = get_config(sys.argv[1])
        auth = HabcamAuthentication(config)
        command = sys.argv[2]
        if command == 'add':
            username = sys.argv[3]
            password = sys.argv[4]
            auth.add_user(username,password)
        elif command == 'delete':
            username = sys.argv[3]
            auth.delete_user(username)
        elif command == 'list':
            for row in auth.list_users():
                # FIXME better display of results, and exclude password and salt columns
                print row
        elif command == 'check':
            username = sys.argv[3]
            password = sys.argv[4]
            if auth.callback(username,password):
                print 'Credentials accepted'
            else:
                print 'Credentials rejected'
    except:
        traceback.print_exc()
        print 'usage: python auth.py [config file] [add|delete|list|check] [username] [password]'
