from flask import Flask, request, url_for, Response
from unittest import TestCase
import json
import re
from oii.utils import gen_id, structs, jsons
from oii.webapi.idgen import idgen_api
from oii import annotation
from oii.times import iso8601
from utils import jsonr

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)
app.register_blueprint(idgen_api)
app.debug = True

# FIXME use real database
db = {}

@app.route('/create_annotations',methods=['POST'])
def create_annotations():
    for ann in json.loads(request.data):
        print 'CREATED '+str(ann)
        db[ann['pid']] = ann
    return '{"status":"OK"}'
    
@app.route('/fetch/annotation/<path:pid>')
def fetch_annotation(pid):
    return jsonr(db[pid])

@app.route('/list_annotations/image/<path:image_pid>')
def list_annotations(image_pid):
    return jsonr([ann for ann in db.values() if ann[annotation.IMAGE] == image_pid])

IMAGE_LIST = [
              'http://molamola.whoi.edu/data/UNQ.20110610.092626156.95900.jpg',
              'http://molamola.whoi.edu/data/UNQ.20110621.174046593.84534.jpg',
              'http://molamola.whoi.edu/data/UNQ.20110627.205454750.84789.jpg',
]
    
@app.route('/list_images')
def list_images():
    return jsonr([{'url':url} for url in IMAGE_LIST])

TAXONOMY = {
            'sand dollar': 'http://foo.bar/ns/sand_dollar',
            'trash': 'http://foo.bar/ns/trash'
}

@app.route('/taxonomy_autocomplete',methods=['GET','POST'])
def taxonomy_autocomplete():
    stem = '^%s.*' % request.values['term']
    return jsonr([{'label': k, 'value': k, 'pid': v} for k,v in TAXONOMY.iteritems() if re.match(stem,k,re.I)])

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
        return structs(timestamp=ts, pid=p, image=i, geometry=b, category=t, annotator=a)
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
            self.app.post(url_for('create_annotations'), data=jsons([ann_in]))
            raw = self.app.get(url_for('fetch_annotation', pid=ann_in.pid)).data
            ann_out = structs(raw)
            assert ann_out.pid == ann_in.pid
            assert ann_out.image == ann_in.image
            assert ann_out.category == ann_in.category
            assert ann_out.annotator == ann_in.annotator
            assert ann_out.timestamp == ann_in.timestamp 
            assert ann_out.geometry == ann_in.geometry
    def test_list_annotations(self):
        with app.test_request_context():
            ns = [0,1,2,3,100]
            image_pids = [gen_id(self.namespace) for _ in range(len(ns))]
            for (n,image_pid) in zip(ns,image_pids):
                # create n annotations for this image pid
                for _ in range(n):
                    ann = self.random_annotation()
                    ann.image = image_pid
                    self.app.post(url_for('create_annotations', pid=ann.pid), data=jsons([ann]))
            for (n,image_pid) in zip(ns,image_pids):
                ann_list = structs(self.app.get(url_for('list_annotations', image_pid=image_pid)).data)
                # FIXME don't just check the length of the result, check the contents
                assert len(ann_list) == n
    def test_list_images(self):
        with app.test_request_context():
            r = structs(self.app.get(url_for('list_images')).data)
            assert [i.url for i in r] == IMAGE_LIST
    def test_autocomplete(self):
        with app.test_request_context():
            for term,url in TAXONOMY.items():
                for i in range(len(term))[2:]:
                    pfx = term[:i]
                    for r in structs(self.app.get(url_for('taxonomy_autocomplete', term=pfx)).data):
                        assert r.label[:i] == pfx
                        assert r.pid == url
                         
if __name__=='__main__':
    app.run()