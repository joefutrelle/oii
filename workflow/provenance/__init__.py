from oii.utils import gen_id

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
BLACKLISTED='blacklisted' # this should not be attempted again
SKIPPED='skipped' # this was skipped for some reason but could be re-attempted

def close_on(status):
    return status in [SUCEEDED, FAILED, BLACKLISTED, SKIP]:

class ProvenanceStore(object):
    def new_process_id(self):
        try:
            return gen_id(self.config.namespace)
        except KeyError:
            return gen_id()
        return (connection,cursor)
    def open_process(self,input_pids=[],algorithm=None,version=None,parameters=None):
        """Create a process. This should be done before attemtping to run the process.
        The initial state of the process is NEW. Algorithm details can be provided here or added later
        using set_algorithm. Same with inputs."""
        pass
    def close_process(self,process_id):
        """Close a process. This sets the closed timestamp to now and so no further events should be
        logged on this process"""
        pass
    def add_algorithm(self,cursor,algorithm,version,parameters=None,comments=None):
        """Add an algorithm. This registers the existence of a version of an algorithm including any parameters that it uses.
        Per-run parameters should be recorded per process id using set_algorithm, and the algorithm and version parameters passed to that
        should match what was passed to add_algorithm."""
        pass
    def set_algorithm(self,process_id,algorithm,version,parameters):
        """Set the per-run algorithm/version/parameters for a given process_id"""
        pass
    def set_status(self,process_id,status,percent_complete=None,log_output=None):
        """Change the status of a process. All parameters except status are optional and will result in NULLs in the event table;
        simply omit them if there is no information to log about them"""
        pass
    def get_status(self,process_id):
        """Get the current status of a process. This is defined as the most recent status logged in the event table"""
        pass
    def add_input(self,process_id,input_pid):
        """Add an input to a process"""
        pass
    def get_inputs(self,process_id):
        """Return the ids of all inputs to the process"""
        pass
    def add_output(self,process_id,input_pid):
        """Add an output to the process"""
        pass
    def get_outputs(self,process_id):
        """Return the IDs of all outputs of a process"""
        pass
