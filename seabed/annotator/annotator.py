
# Start simple with making the existing annotation tool work.

from os import urandom
from sys import argv
from oii.config import get_config
from oii.webapi.annotation import app 
from oii.webapi.annotation import ANNOTATION_STORE, CATEGORIES, ASSIGNMENT_STORE
from oii.seabed.annotation.assignments import SeabedAssignmentStore 
from oii.seabed.annotation.categories import SeabedCategories
from oii.seabed.annotation.annotation import SeabedAnnotationStore

if __name__ == '__main__':

    config = get_config(argv[1])

    app.config[ANNOTATION_STORE] = SeabedAnnotationStore(config)
    app.config[ASSIGNMENT_STORE] = SeabedAssignmentStore(config)
    app.config[CATEGORIES] = SeabedCategories(config) 
    
    app.secret_key = urandom(24)
    app.run(host=config.interface,port=int(config.port))
