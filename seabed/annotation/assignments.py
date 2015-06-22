
from oii.habcam.assignments import HabcamAssignmentStore

# subclass from habcam. functional changes may come later
# ideally habcam and seabed would both subclass from a
# general purpose db backed storage class.

class SeabedAssignmentStore(HabcamAssignmentStore):
    def __init__(self,config):
        HabcamAssignmentStore.__init__(self,config)
