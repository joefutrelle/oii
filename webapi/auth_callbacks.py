from oii.psql import xa

class Authentication(object):
    def callback(self,username,password):
        return True

class PsqlAuthentication(object):
    """config must contain psql_connect.
    query should be a query that returns a result with >0 rows if the user
    is authorized. the query must be parameterized by username and password,
    in that order. e.g.,
    SELECT * FROM my_user_table WHERE name=%s AND pwd=md5(salt || %s)"""
    def __init__(self,config,query):
        self.config = config
        self.query = query
    def callback(self,username,password):
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute(self.query,(username,password))
            for row in cursor.fetchall():
                return True
            # if we reach this, there were no responses
            return False
        
