from flask import Flask, request, url_for, abort, session
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
from oii.utils import md5_string
from utils import jsonr, UrlConverter
import urllib

# FIXME DEBUG
from oii.psql import xa

# test with IFCB
#from oii.ifcb.annotation import IfcbCategories, IfcbFeedAssignmentStore

# test with Habcam
from oii.habcam.assignments import HabcamAssignmentStore
from oii.habcam.categories import HabcamCategories
from oii.habcam.annotation import HabcamAnnotationStore

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)
app.url_map.converters['url'] = UrlConverter
app.register_blueprint(idgen_api)
app.register_blueprint(auth_api)
app.debug = True

# importantly, set max-age on static files (e.g., javascript) to something really short
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30

# config options
CONFIG = 'config' # raw config object stored in app config object
ANNOTATION_STORE = 'annotation_store'
CATEGORIES = 'categories'
ASSIGNMENT_STORE = 'assignment_store'

# default config
DEFAULT_CONFIG = {
    ANNOTATION_STORE: DebugAnnotationStore(),
}

def authme(u,p):
    valid = [
        ('joe','aa31baffe11ee1aa6ed1e00e87bae16e'),
        ('yorksea','f477dcb057f22c8083b2aa00e45bbad8')
        ]
    return (u,md5_string(p)) in valid

auth_api.auth_callback = authme

# get a configured component, or use a default one for testing
def my(key):
    if key in app.config:
        return app.config[key]
    else:
        return DEFAULT_CONFIG[key]

@app.route('/create_annotations',methods=['POST'])
def create_annotations():
    annotations = json.loads(request.data)
    # indicate that they're by the session user
    try:
        for ann in annotations:
            ann['annotator'] = session['username']
    except KeyError:
        abort(401)
    # writem
    my(ANNOTATION_STORE).create_annotations(annotations)
    return '{"status":"OK"}'
    
@app.route('/fetch/annotation/<url:pid>')
def fetch_annotation(pid):
    return jsonr(my(ANNOTATION_STORE).fetch_annotation(pid))

@app.route('/deprecate/annotation/<url:pid>')
def deprecate_annotation(pid):
    # return jsonr(my(ANNOTATION_STORE).deprecate_annotation(pid))
    my(ANNOTATION_STORE).deprecate_annotation(pid)
    return '{"status":"OK"}'

def hardcodeme(image_pid):
    yield image_pid
    with xa(app.config[CONFIG].psql_connect) as (connection, cursor):
        cursor.execute("select image_id, scope_id, category_id, geometry_text, annotator_id, to_char(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"hh:MI:ss\"Z\"') as timestamp, assignment_id, annotation_id, deprecated from annotations where image_id = %s",('http://habcam-data.whoi.edu/data/UNQ.20110608.072618109.03524.jpg',))
        for ann in cursor.fetchall():
            yield ann

@app.route('/foobar_baz/image/<url:image_pid>')
def foobar_baz(image_pid):
    return jsonr([image_pid])

@app.route('/list_annotations/image/<url:image_pid>')
@app.route('/list_annotations/image/<url:image_pid>/assignment/<url:assignment_pid>')
def list_annotations(image_pid,assignment_pid=None):
    if assignment_pid is not None:
        return jsonr(list(my(ANNOTATION_STORE).list_annotations(image=image_pid,assignment=assignment_pid)))
    else:
        return jsonr(list(my(ANNOTATION_STORE).list_annotations(image=image_pid)))

@app.route('/fetch_assignment/<path:assignment_pid>')
def fetch_assignment(assignment_pid):
    return jsonr(my(ASSIGNMENT_STORE).fetch_assignment(assignment_pid))

@app.route('/list_images/limit/<int:limit>/offset/<int:offset>/assignment/<path:assignment_pid>')
@app.route('/list_images/limit/<int:limit>/offset/<int:offset>/status/<status>/assignment/<path:assignment_pid>')
def list_images(limit,offset,assignment_pid,status=None):
    return jsonr(list(my(ASSIGNMENT_STORE).list_images(assignment_pid,limit,offset,status)))

@app.route('/find_image/offset/<int:offset>/status/<status>/assignment/<path:assignment_pid>')
def find_image(offset,status,assignment_pid):
    return jsonr(dict(offset=my(ASSIGNMENT_STORE).find_image(assignment_pid,offset,status)))

@app.route('/set_status/image/<path:image_id>/status/<status>/assignment/<path:assignment_id>')
def set_status(assignment_id,image_id,status):
    assignment_id = urllib.unquote(assignment_id)
    status = urllib.unquote_plus(status)
    my(ASSIGNMENT_STORE).set_status(assignment_id,image_id,status)
    return jsonr(dict(status='OK',new_image_status=status))

@app.route('/list_assignments')
def list_assignments():
    return jsonr({'assignments': my(ASSIGNMENT_STORE).list_assignments()})

def stem_search(stem,mode,scope=None):
    for c in my(CATEGORIES).list_categories(mode,scope):
        if re.match(r'.*\b'+stem,c['label'],re.I):
            yield {
                'pid': c['pid'],
                'label': c['label'],
                'value': c['label']
            }

@app.route('/list_categories/<mode>')
@app.route('/list_categories/<mode>/<scope>')
def list_categories(mode,scope=None):
    return jsonr(list(my(CATEGORIES).list_categories(mode,scope)))

@app.route('/category_autocomplete/<mode>',methods=['GET','POST'])
@app.route('/category_autocomplete/<mode>/<scope>',methods=['GET','POST'])
def category_autocomplete(mode,scope=None):
    stem = request.values['term']
    return jsonr(list(stem_search(stem,mode,scope)))

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
            assert ann_out.scope == ann_in.scope
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

def config_backend(config):
    try:
        app.config[CONFIG] = config
        app.config[ANNOTATION_STORE] = HabcamAnnotationStore(config)
        app.config[ASSIGNMENT_STORE] = HabcamAssignmentStore(config)
        app.config[CATEGORIES] = HabcamCategories(config)
    except KeyError:
        pass # FIXME log error

app.secret_key = os.urandom(24)

if __name__=='__main__':
    if len(sys.argv) > 1:
        config = get_config(sys.argv[1])
        config_backend(config)
        try:
            port = int(config.port)
        except KeyError:
            port = 5000
    app.run(host='0.0.0.0',port=port)
else:
    config = get_config(os.environ['ANNOTATOR_CONFIG_FILE'])
    config_backend(config)

