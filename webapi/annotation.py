from flask import Flask, request, g
from unittest import TestCase
import json
import re
from oii.utils import gen_id
from oii.times import iso8601

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)

# FIXME use real database
db = {}

# FIXME express annotation information model schema elsewhere (not in webapp code)
PID = 'pid'
TIMESTAMP = 'timestamp'
ANNOTATOR = 'annotator'
IDENTIFICATION = 'identification'
BOUNDING_BOX = 'boundingBox'
IMAGE = 'image'

@app.route('/generate_ids/<int:n>')
@app.route('/generate_ids/<int:n>/<path:ns>')
def generate_ids(n,ns=''):
    return json.dumps([ns + gen_id() for _ in range(n)])

@app.route('/create_annotation/<path:id>',methods=['POST'])
def create_annotation(id):
    annotation = json.loads(request.data)
    print 'POST %s: %s' % (id, json.dumps(annotation)) # FIXME write a log
    db[id] = annotation
    
@app.route('/fetch/annotation/<path:id>')
def fetch_annotation(id):
    return json.dumps(db[id])

@app.route('/list_annotations/image/<path:image_id>')
def list_annotations(image_id):
    return json.dumps([ann for ann in db.values if ann[IMAGE] == image_id])

class TestAnnotation(TestCase):
    def setUp(self):
        self.namespace = 'http://foo.bar.baz/fnord/'
        self.app = app.test_client()
    def random_annotation(self):
        ann = {}
        ann[PID] = gen_id(self.namespace)
        ann[IMAGE] = gen_id(self.namespace)
        ann[BOUNDING_BOX] = [(123,234), (345,456)] # doesn't matter what these are
        ann[IDENTIFICATION] = gen_id(self.namespace)
        ann[ANNOTATOR] = gen_id(self.namespace)
        ann[TIMESTAMP] = iso8601()
        return ann
    def test_gen_ids(self):
        ids = json.loads(self.app.get('/generate_ids/20/%s' % self.namespace).data)
        assert len(ids) == 20
        for id in ids:
            assert len(id) == len(self.namespace) + 40
            assert re.match('[a-f0-9]+',id[len(self.namespace):])
    def test_create_fetch(self):
        ann_in = self.random_annotation()
        pid = ann_in[PID]
        url = '/create_annotation/%s' % pid
        self.app.post(url, data=json.dumps(ann_in))
        ann_out = json.loads(self.app.get('/fetch/annotation/%s' % pid).data)
        assert ann_out[PID] == ann_in[PID]
        assert ann_out[IMAGE] == ann_in[IMAGE]
        # FIXME deal with bounding box (simple == doesn't survive JSON roundtripping)
        assert ann_out[IDENTIFICATION] == ann_in[IDENTIFICATION]
        assert ann_out[ANNOTATOR] == ann_in[ANNOTATOR]
        assert ann_in[TIMESTAMP] == ann_out[TIMESTAMP]
    def test_list_annotations(self):
        pass

if __name__=='__main__':
    app.run()