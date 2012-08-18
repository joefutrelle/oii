
# Start simple, by making the existing annotation tool work.
# requested config example in task 1604
# https://beagle.whoi.edu/redmine/issues/1604

from os import urandom
from sys import argv
from oii.config import get_config
from oii.webapi.annotation import app 
from oii.webapi.annotation import ANNOTATION_STORE, CATEGORIES, ASSIGNMENT_STORE
from oii.seabed.assignments import SeabedAssignmentStore 
from oii.seabed.categories import SeabedCategories
from oii.seabed.annotation import SeabedAnnotationStore

if __name__ == '__main__':

    config = get_config(argv[1])

    app.config[ANNOTATION_STORE] = SeabedAnnotationStore(config)
    app.config[ASSIGNMENT_STORE] = SeabedAssignmentStore(config)
    app.config[CATEGORIES] = SeabedCategories(config) 
    
    app.secret_key = urandom(24)
    app.run(host='0.0.0.0',port=1234)
