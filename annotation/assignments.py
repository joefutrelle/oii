
        
# abstract API for representing assignments
class AssignmentStore(object):
    def ___init__(self):
        self.assignments = [{
            "pid": "http://foo.bar/assignments/baz",
            "label": "Identify quux for images from fnord cruise",
            "annotator": "Ann O. Tator",
            "status": "new",
            "images": [{
                 "pid": "http://foo.bar/images/abcdef",
                 "image": "http://foo.bar/images/abcdef.jpg"
            }]
        }]
    def list_assignments(self):
        return self.assignments