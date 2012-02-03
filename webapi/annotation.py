from flask import Flask, request, url_for
from unittest import TestCase
import json
import re
from oii.utils import gen_id
from oii.times import iso8601
from oii.webapi.idgen import idgen_api

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)
app.register_blueprint(idgen_api)

# FIXME use real database
db = {}

# FIXME express annotation information model schema elsewhere (not in webapp code)
PID = 'pid'
TIMESTAMP = 'timestamp'
ANNOTATOR = 'annotator'
IDENTIFICATION = 'identification'
BOUNDING_BOX = 'boundingBox'
IMAGE = 'image'

@app.route('/create_annotation/<path:pid>',methods=['POST'])
def create_annotation(pid):
    annotation = json.loads(request.data)
    #print 'POST %s: %s' % (pid, json.dumps(annotation)) # FIXME write a log
    db[pid] = annotation
    
@app.route('/fetch/annotation/<path:pid>')
def fetch_annotation(pid):
    return json.dumps(db[pid])

@app.route('/list_annotations/image/<path:image_pid>')
def list_annotations(image_pid):
    return json.dumps([ann for ann in db.values() if ann[IMAGE] == image_pid])

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
        with app.test_request_context():
            ids = json.loads(self.app.get(url_for('idgen_api.generate_ids', n=20, ns=self.namespace)).data)
            #ids = json.loads(self.app.get('/generate_ids/%d/%s' % (20, self.namespace)).data)
            assert len(ids) == 20 # we asked for 20
            for id in ids:
                assert len(id) == len(self.namespace) + 40 # sha1 hashes are 160 bits, hex-encoded 40 chars
                assert re.match('[a-f0-9]+',id[len(self.namespace):],re.I) # hex encoded
    def test_create_fetch(self):
        with app.test_request_context():
            ann_in = self.random_annotation()
            pid = ann_in[PID]
            self.app.post(url_for('create_annotation', pid=pid), data=json.dumps(ann_in))
            ann_out = json.loads(self.app.get(url_for('fetch_annotation', pid=pid)).data)
            assert ann_out[PID] == ann_in[PID]
            assert ann_out[IMAGE] == ann_in[IMAGE]
            # FIXME deal with bounding box (simple == doesn't survive JSON roundtripping)
            assert ann_out[IDENTIFICATION] == ann_in[IDENTIFICATION]
            assert ann_out[ANNOTATOR] == ann_in[ANNOTATOR]
            assert ann_in[TIMESTAMP] == ann_out[TIMESTAMP]
    def test_list_annotations(self):
        with app.test_request_context():
            ns = [0,1,2,3,100]
            image_pids = [gen_id(self.namespace) for _ in range(len(ns))]
            for (n,image_pid) in zip(ns,image_pids):
                # create n annotations for this image pid
                for _ in range(n):
                    ann = self.random_annotation()
                    ann[IMAGE] = image_pid
                    self.app.post(url_for('create_annotation', pid=ann[PID]), data=json.dumps(ann))
            for (n,image_pid) in zip(ns,image_pids):
                ann_list = json.loads(self.app.get(url_for('list_annotations', image_pid=image_pid)).data)
                # FIXME don't just check the length of the result, check the contents
                assert len(ann_list) == n

if __name__=='__main__':
    app.run()