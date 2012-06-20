from oii.utils import gen_id
import psycopg2 as psql

'''
Provenance tracking API.
The basic model is that of the Open Provenance Model.
A provenance record states that a product was produced from 0 or more inputs via some process.
That process has metadata describing what kind of processing ran, when it ran, and
its completion / success status.
All input and output datasets must have permanent, globally-unique IDs.
Each process has an ID too.
A process cannot be re-run or re-started. That counts as a new process.
'''

# status settings

NEW='new' # never attempted
PENDING='pending' # starting
RUNNING='running' # in process
SUCCEEDED='succeeded' # completed, succeeded
FAILED='failed' # completed, failed
STOPPED='stopped' # halted, interrupted, or suspended during processing
REJECTED='rejected' # did not complete, should not re-attempt. different from failure

class ProvenanceStore(object):
    def __init__(self,config):
        self.config = config
    def new_process_id(self):
        try:
            return gen_id(self.config.namespace)
        except KeyError:
            return gen_id()
    def __connect(self):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        return (connection,cursor)
    def open_process(self,input_pids=[],algorithm=None,version=None,parameters=None):
        process_id = self.new_process_id()
        (connection, cursor) = self.__connect()
        self.__create_process(cursor,process_id)
        self.__set_status(cursor,process_id,NEW)
        self.__set_algorithm(cursor,process_id,algorithm,version,parameters)
        for input_pid in input_pids:
            self.__add_input(cursor,process_id,input_pid)
        connection.commit()
        return process_id
    def close_process(self,process_id)
        (connection, cursor) = self.__connect()
        self.__close_process(process_id)
    def __close_process(self,cursor,process_id):
        cursor.execute('update processes set closed=now()')
    def __create_process(self,cursor,process_id):
        cursor.execute('insert into processes (process_id,opened) values (%s,now())',(process_id,))
    def __set_status(self,cursor,process_id,status,log_output=''):
        cursor.execute('insert into events (process_id,when,status,log_output) values (%s,now(),%s,%s)',(process_id,status,log_output))
    def __set_algorithm(self,cursor,process_id,algorithm,version,parameters):
        cursor.execute('update processes set algorithm=%s, version=%s, parameters=%s where process_id=%s',(algorithm,version,parameters,process_id))
    def __add_input(self,cursor,process_id,input_pid):
        cursor.execute('insert into inputs (process_id, input_pid) values (%s,%s)',(process_id,input_pid))
    def set_status(self,process_id,status,log_output=''):
        (_, cursor) = self.__connect()
        self.__set_status(cursor,process_id,status,log_output)
        if status in [SUCCEEDED, FAILED, STOPPED, REJECTED]:
            self.__close_process(process_id)
    def get_status(self,process_id):
        (_, cursor) = self.__connect()
        cursor.execute('select status from events where process_id=%s order by observed desc limit 1')
        for row in cursor.fetchall():
            return row[0]
        raise KeyError('no such process %s' % process_id)

