from oii.utils import gen_id
from oii.psql import xa
from oii.provenance import NEW, PENDING, RUNNING, SUCCEEDED, FAILED, BLACKLISTED, SKIPPED, close_on
import psycopg2 as psql

class PsqlProvenanceStore(ProvenanceStore):
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
        """Create a process. This should be done before attemtping to run the process.
        The initial state of the process is NEW. Algorithm details can be provided here or added later
        using set_algorithm. Same with inputs."""
        process_id = self.new_process_id()
        with xa(self.config.psql_connect) as (connection,cursor):
            self.__create_process(cursor,process_id)
            self.__set_status(cursor,process_id,NEW)
            self.__set_algorithm(cursor,process_id,algorithm,version,parameters)
            for input_pid in input_pids:
                self.__add_input(cursor,process_id,input_pid)
            connection.commit()
        return process_id
    def close_process(self,process_id):
        """Close a process. This sets the closed timestamp to now and so no further events should be
        logged on this process"""
        with xa(self.config.psql_connect) as (connection,cursor):
            self.__close_process(cursor, process_id)
            connection.commit()
    def __close_process(self,cursor,process_id):
        cursor.execute('update processes set closed=now()')
    def __create_process(self,cursor,process_id):
        cursor.execute('insert into processes (process_id,opened) values (%s,now())',(process_id,))
    def __set_status(self,cursor,process_id,status,percent_complete=None,log_output=None):
        cursor.execute('insert into events (process_id,when,status,percent_complete,log_output) values (%s,now(),%s,%s,%s)',(process_id,status,percent_complete,log_output))
    def __set_algorithm(self,cursor,process_id,algorithm,version,parameters):
        cursor.execute('update processes set algorithm=%s, version=%s, parameters=%s where process_id=%s',(algorithm,version,parameters,process_id))
    def __add_input(self,cursor,process_id,input_pid):
        cursor.execute('insert into used (process_id, pid) values (%s,%s)',(process_id,input_pid))
    def __add_output(self,cursor,process_id,output_pid):
        cursor.execute('insert into generated_by (process_id, pid) values (%s,%s)',(process_id,output_pid))
    def __add_algorithm(self,cursor,algorithm,version,parameters=None):
        cursor.execute('insert into algorithms (algorithm, version, parameters) values (%s,%s,%s)',(algorithm,version,parameters))
    def add_algorithm(self,cursor,algorithm,version,parameters=None,comments=None):
        """Add an algorithm. This registers the existence of a version of an algorithm including any parameters that it uses.
        Per-run parameters should be recorded per process id using set_algorithm, and the algorithm and version parameters passed to that
        should match what was passed to add_algorithm."""
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('insert into algorithms (algorithm, version, parameters, comments) values (%s,%s,%s)',(algorithm,version,parameters,comments))
            connection.commit()
    def set_algorithm(self,process_id,algorithm,version,parameters):
        """Set the per-run algorithm/version/parameters for a given process_id"""
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('update processes set algorithm=%s, version=%s, parameters=%s where process_id=%s',(algorithm,version,parameters,process_id))
            connection.commit()
    def set_status(self,process_id,status,percent_complete=None,log_output=None):
        """Change the status of a process. All parameters except status are optional and will result in NULLs in the event table;
        simply omit them if there is no information to log about them"""
        with xa(self.config.psql_connect) as (connection,cursor):
            self.__set_status(cursor,process_id,status,percent_complete,log_output)
            if close_on(status):
                self.__close_process(process_id)
            connection.commit()
    def get_status(self,process_id):
        """Get the current status of a process. This is defined as the most recent status logged in the event table"""
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select status from events where process_id=%s order by observed desc limit 1')
            for row in cursor.fetchall():
                return row[0]
            raise KeyError('no such process %s' % process_id)
    def add_input(self,process_id,input_pid):
        """Add an input to a process"""
        with xa(self.config.psql_connect) as (connection,cursor):
            self.__add_input(process_id, input_pid)
            connection.commit()
    def get_inputs(self,process_id):
        """Return the ids of all inputs to the process"""
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select pid from used where process_id=%s',(process_id,))
            return [row[0] for row in cursor.fetchall()]
    def add_output(self,process_id,input_pid):
        """Add an output to the process"""
        with xa(self.config.psql_connect) as (connection,cursor):
            self.__add_output(process_id, input_pid)
            connection.commit()
    def get_outputs(self,process_id):
        """Return the IDs of all outputs of a process"""
        with xa(self.config.psql_connect) as (connection,cursor):
            cursor.execute('select pid from generated_by where process_id=%s',(process_id,))
            return [row[0] for row in cursor.fetchall()]

