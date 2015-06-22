
from oii.habcam.annotation import HabcamAnnotationStore

# subclass from habcam. functional changes may come later
# ideally habcam and seabed would both subclass from a 
# general purpose db backed storage class.

class SeabedAnnotationStore(HabcamAnnotationStore):
    def __init__(self,config):
        HabcamAnnotationStore.__init__(self,config)
