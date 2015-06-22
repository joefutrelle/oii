from oii.annotation.categories import Categories
from oii.annotation.assignments import AssignmentStore

class DummyCategories(Categories):
    def list_categories(self,_):
        return [{
            'label': 'sand dollar',
            'pid': 'http://foo.bar/ns/sand_dollar'
        },{
            'label': 'trash',
            'pid': 'http://foo.bar/ns/trash'
        }]

class DummyAssignmentStore(AssignmentStore):
    def __init__(self):
        self.assignments = [{
            "pid": "http://foo.bar/assignments/baz",
            "label": "Look for trash",
            "status": "new",
            "mode": "trash",
            "images": [{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110610.092626156.95900.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110610.092626156.95900.jpg"
                },{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110621.174046593.84534.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110621.174046593.84534.jpg"
                },{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110627.205454750.84789.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110627.205454750.84789.jpg"
                }]
          },{
            "pid": "http://foo.bar/assignments/fnordy",
            "label": "Look for sand dollars",
            "status": "new",
            "mode": "sanddollars",
            "images": [{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110610.092626156.95900.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110610.092626156.95900.jpg"
                },{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110621.174046593.84534.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110621.174046593.84534.jpg"
                },{
                 "pid": "http://molamola.whoi.edu/data/UNQ.20110627.205454750.84789.jpg",
                 "image": "http://molamola.whoi.edu/data/UNQ.20110627.205454750.84789.jpg"
                }]
          }]
          
class ZoomAssignmentStore(AssignmentStore):
    def __init__(self):
        self.assignments = [{
            "pid": "http://foo.bar/assignments/baz",
            "label": "Zoom Testing",
            "status": "new",
            "mode": "trash",
            "images": [{
                 "pid": "http://localhost:5000/static/images/zoom/zoom-test.jpg",
                 "image": "http://localhost:5000/static/images/zoom/zoom-test.jpg"
                }]
          }]
        
