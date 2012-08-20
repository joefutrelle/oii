
from oii.habcam.categories import HabcamCategories

# subclass from habcam. functional changes may come later
# ideally habcam and seabed would both subclass from a
# general purpose db backed storage class.

class SeabedCategories(HabcamCategories):
    def __init__(self,config):
        HabcamCategories.__init__(self,config)

