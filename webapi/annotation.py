from flask import Flask, request, url_for
from unittest import TestCase
import json
import re
import sys
import os
from oii.utils import gen_id, structs, jsons
from oii.config import get_config
from oii.webapi.idgen import idgen_api
from oii.webapi.auth import auth_api
from oii.annotation.storage import DebugAnnotationStore
from oii.annotation.psql import PsqlAnnotationStore
from oii.annotation.categories import Categories
from oii.annotation.assignments import AssignmentStore
from oii.times import iso8601
from utils import jsonr

# test with IFCB
#from oii.ifcb.annotation import IfcbCategories, IfcbFeedAssignmentStore

# test with Habcam
from oii.habcam.assignments import HabcamAssignmentStore
from oii.habcam.categories import HabcamCategories

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)
app.register_blueprint(idgen_api)
app.register_blueprint(auth_api)
app.debug = True

# config options
ANNOTATION_STORE = 'annotation_store'
CATEGORIES = 'categories'
ASSIGNMENT_STORE = 'assignment_store'

# default config
DEFAULT_CONFIG = {
    ANNOTATION_STORE: DebugAnnotationStore(),
}

# get a configured component, or use a default one for testing
def my(key):
    if key in app.config:
        return app.config[key]
    else:
        return DEFAULT_CONFIG[key]

@app.route('/create_annotations',methods=['POST'])
def create_annotations():
    my(ANNOTATION_STORE).create_annotations(json.loads(request.data))
    return '{"status":"OK"}'
    
@app.route('/fetch/annotation/<path:pid>')
def fetch_annotation(pid):
    return jsonr(my(ANNOTATION_STORE).fetch_annotation(pid))

@app.route('/list_annotations/image/<path:image_pid>')
def list_annotations(image_pid):
    return jsonr(list(my(ANNOTATION_STORE).list_annotations(image=image_pid)))

@app.route('/fetch_assignment/<path:assignment_pid>')
def fetch_assignment(assignment_pid):
    return jsonr(my(ASSIGNMENT_STORE).fetch_assignment(assignment_pid))

@app.route('/list_images/limit/<int:limit>/offset/<int:offset>/assignment/<path:assignment_pid>')
def list_images(limit,offset,assignment_pid):
    return jsonr(list(my(ASSIGNMENT_STORE).list_images(assignment_pid,limit,offset)))

@app.route('/list_assignments')
def list_assignments():
    return jsonr({'assignments': my(ASSIGNMENT_STORE).list_assignments()})

def stem_search(stem,mode):
    for c in my(CATEGORIES).list_categories(mode):
        if re.match(stem,c['label'],re.I):
            yield {
                'pid': c['pid'],
                'label': c['label'],
                'value': c['label']
            }

@app.route('/list_categories/<path:mode>')
def list_categories(mode):
    return jsonr(list(my(CATEGORIES).list_categories(mode)))

@app.route('/category_autocomplete/<path:mode>',methods=['GET','POST'])
def category_autocomplete(mode):
    stem = '^%s.*' % request.values['term']
    return jsonr(list(stem_search(stem,mode)))

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
            image_list = [i['image'] for i in my(ASSIGNMENT_STORE).list_assignments()[0]['images']]
            assert [i.image for i in r.images] == image_list
    def test_autocomplete(self):
        with app.test_request_context():
            for term,url in [(c['label'],c['pid']) for c in my(CATEGORIES).list_categories()]:
                for i in range(len(term))[2:]:
                    pfx = term[:i]
                    for r in structs(self.app.get(url_for('taxonomy_autocomplete', term=pfx)).data):
                        assert r.label[:i] == pfx
                        assert r.pid == url
                         
if __name__=='__main__':
    if len(sys.argv) > 1:
        config = get_config(sys.argv[1])
        try:
            app.config[ANNOTATION_STORE] = DebugAnnotationStore()
            app.config[ASSIGNMENT_STORE] = HabcamAssignmentStore(config)
            app.config[CATEGORIES] = HabcamCategories(config)
        except KeyError:
            pass
        try:
            port = int(config.port)
        except KeyError:
            port = 5000
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0',port=port)
