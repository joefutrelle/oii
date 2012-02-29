from oii import annotation
from oii.utils import SimpleStore

# abstract API for storing, querying, and creating annotations
class AnnotationStore(object):
    def list_annotations(self,template):
        "List annotations which match the given template (flat dictionary, k/v's in template must match k/v's in candidate"
        raise KeyError('no matching annotations')
    def fetch_annotation(self,annotation_pid):
        "Fetch an annotation by its PID"
        raise KeyError('unknown annotation ' + annotation_pid)
    def create_annotations(self,annotations):
        "Create annotations"
        pass

# stores annotations in temporary in-memory data structure
class DebugAnnotationStore(AnnotationStore):
    store = SimpleStore(annotation.PID)
    def list_annotations(self,**template):
        return self.store.list(**template)
    def fetch_annotation(self,annotation_pid):
        return self.store.fetch(annotation_pid)
    def create_annotations(self,annotations):
        self.store.addEach(annotations)

