# utilities for oii
from threading import local
import os
import re
from hashlib import sha1
from time import time, clock
from unittest import TestCase

genid_prev_id_tl = local()
prev = genid_prev_id_tl.prev = None

def gen_id(namespace=''):
    prev = genid_prev_id_tl.prev
    if prev is None:
        prev = sha1(os.urandom(24)).hexdigest()
    else:
        entropy = str(clock()) + str(time()) + str(os.getpid())
        prev = sha1(prev + entropy).hexdigest()
    genid_prev_id_tl.prev = prev
    return namespace + prev

class test_gen_id(TestCase):
    # run collision test
    def test_all(self):
        for ns in ['', 'http://foo.bar/quux#']:
            ids = []
            len = 5000
            while len > 0:
                len -= 1
                new_id = gen_id(ns)
                assert new_id not in ids
                ids.append(new_id)

# due to http://stackoverflow.com/a/1305663 
# useful to a point; for denormalized, table-like data           
class Struct():
    def from_dict(self, d):
        self.__dict__.update(d)
        
    def as_dict(self):
        return self.__dict__
        
    def __init__(self, d=None, **kv):
        if d is not None:
            self.from_dict(d)
        else:
            self.from_dict(kv)

class Destruct(dict):
    def __init__(self,struct):
        self.update(struct.as_dict())
        
class TestStruct(TestCase):
    def test_init_kw(self):
        s = Struct(a=3, b=4)
        assert s.a == 3
        assert s.b == 4
    def test_init_dict(self):
        s = Struct(dict(b=2, x='flaz'))
        assert s.b == 2
        assert s.x == 'flaz'
    def test_destruct(self):
        s = Struct(dict(b=2, x='flaz'))
        assert Destruct(s) == dict(x='flaz', b=2)

def dict_slice(d,schema):
    """d - a dict to slice
    keys - the keys to slice, or if a dict, a dict mapping those keys to functions to call on the values first"""
    if type(schema) == str:
        schema = re.split(',',schema)
    if type(schema) == list:
        return dict((k,v) for k,v in d.iteritems() if k in schema)
    if type(schema) == dict:
        xf = dict((k,schema[k](d[k])) for k in schema.keys() if schema[k] is not None)
        xf.update(dict((k,d[k]) for k in schema.keys() if schema[k] is None))
        return xf
    
class TestDictSlice(TestCase):
    def test_list(self):
        d = dict(a=3, b=7, c=8)
        k = ['a','c']
        s = dict_slice(d,k)
        assert s == dict(a=3, c=8)
    def test_str(self):
        d = dict(a=3, b=7, c=8)
        k = 'b,c'
        s = dict_slice(d,k)
        assert s == dict(b=7, c=8)
    def test_map(self):
        d = dict(a=3, b=7, c=8)
        m = dict(a=lambda x: x+2, b=str, c=None)
        s = dict_slice(d,m)
        assert s == dict(a=5,b='7',c=8)
        