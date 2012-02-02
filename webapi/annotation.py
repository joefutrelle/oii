from flask import Flask
import os
from unittest import TestCase

"""Prototype annotation web API
see https://beagle.whoi.edu/redmine/issues/948
and https://beagle.whoi.edu/redmine/issues/943"""

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

class TestApi(TestCase):
    def setUp(self):
        self.app = app.test_client()
    def tearDown(self):
        pass
        
class TestAnnotation(TestApi):
    def test_hw(self):
        assert self.app.get('/').data == 'Hello World!'
