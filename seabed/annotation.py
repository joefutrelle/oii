
from oii.habcam.annotation import HabcamAnnotationStore

class SeabedAnnotationStore(HabcamAnnotationStore):
    def __init__(self,config):
        HabcamAnnotationStore.__init__(self,config)
