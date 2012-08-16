
from oii.habcam.assignments import HabcamAssignmentStore

class SeabedAssignmentStore(HabcamAssignmentStore):
    def __init__(self,config):
        HabcamAssignmentStore.__init__(self,config)
