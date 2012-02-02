from flask import Flask
from unittest import TestCase
from oii.utils import gen_id
import json
import re

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/generate_ids/<int:n>')
def generate_ids(n):
    return json.dumps([gen_id() for _ in range(n)])
    
class TestApi(TestCase):
    def setUp(self):
        self.app = app.test_client()
    def tearDown(self):
        pass
        
class TestAnnotation(TestApi):
    def test_hw(self):
        assert self.app.get('/').data == 'Hello World!'
    def test_gen_ids(self):
        ids = json.loads(self.app.get('/generate_ids/20').data)
        assert len(ids) == 20
        for id in ids:
            assert len(id) == 40
            assert re.match('[a-f0-9]+',id)
