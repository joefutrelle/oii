from flask import Flask, request, url_for
from unittest import TestCase
import json
import re
from oii.utils import gen_id, Struct, Destruct
from oii.webapi.idgen import idgen_api
from oii import annotation
from oii.times import iso8601

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)
app.register_blueprint(idgen_api)

# FIXME use real database
db = {}

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
    return json.dumps([ann for ann in db.values() if ann[annotation.IMAGE] == image_pid])

class TestAnnotation(TestCase):
    def setUp(self):
        self.namespace = 'http://foo.bar.baz/fnord/'
        self.app = app.test_client()
    def random_annotation(self):
        p = gen_id(self.namespace)
        i = gen_id(self.namespace)
        b = [[123,234], [345,456]] # tuples do not survive JSON roundtripping
        t = gen_id(self.namespace)
        a = gen_id(self.namespace)
        ts = iso8601()
        return Struct(timestamp=ts, pid=p, image=i, geometry=b, taxon=t, annotator=a)
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
            pid = ann_in.pid
            self.app.post(url_for('create_annotation', pid=pid), data=json.dumps(Destruct(ann_in)))
            ann_out = Struct(json.loads(self.app.get(url_for('fetch_annotation', pid=pid)).data))
            assert ann_out.pid == ann_in.pid
            assert ann_out.image == ann_in.image
            assert ann_out.taxon == ann_in.taxon
            assert ann_out.annotator == ann_in.annotator
            assert ann_out.timestamp == ann_in.timestamp 
            assert ann_out.geometry == ann_in.geometry
            # FIXME deal with bounding box (simple == doesn't survive JSON roundtripping)
    def test_list_annotations(self):
        with app.test_request_context():
            ns = [0,1,2,3,100]
            image_pids = [gen_id(self.namespace) for _ in range(len(ns))]
            for (n,image_pid) in zip(ns,image_pids):
                # create n annotations for this image pid
                for _ in range(n):
                    ann = self.random_annotation()
                    ann.image = image_pid
                    self.app.post(url_for('create_annotation', pid=ann.pid), data=json.dumps(Destruct(ann)))
            for (n,image_pid) in zip(ns,image_pids):
                ann_list = [Struct(ann) for ann in json.loads(self.app.get(url_for('list_annotations', image_pid=image_pid)).data)]
                # FIXME don't just check the length of the result, check the contents
                assert len(ann_list) == n

if __name__=='__main__':
    app.run()