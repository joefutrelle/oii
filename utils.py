# utilities for oii
from threading import local
import os
import re
from hashlib import sha1
from time import time, clock
from unittest import TestCase
import json

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
# with enhancements. Struct class provides view of JSON or JSON-like structure that allows
# direct member access. So a JSON structure {"foo":["bar":{"baz":7}]}
# could be accessed like ref.foo[0].baz

# note that if your JSON endpoint returns a non-dict (e.g., a list) pass it to the
# structs factory instead of calling Struct's initializer

def structs(item):
    if type(item) == dict:
        return Struct(item)
    elif type(item) == list:
        return map(structs,item)
    elif type(item) == tuple:
        return tuple(map(structs,item))
    else:
        return item

class Struct():
    def __from_dict(self, d):
        for k,v in d.items():
            self.__dict__[k] = structs(v)
        
    @property
    def as_dict(self):
        result = {}
        for k,v in self.__dict__.iteritems():
            if type(v) == Struct:
                result[k] = v.as_dict
            elif type(v) == list:
                result[k] = map(lambda e: e.as_dict if isinstance(e,Struct) else e, v)
            elif type(v) == tuple:
                result[k] = tuple(map(lambda e: e.as_dict if isinstance(e,Struct) else e,v))
            else:
                result[k] = v
        return result
    
    @property
    def json(self):
        return json.dumps(self.as_dict)
    
    def __repr__(self):
        return self.json
    
    def __init__(self, d=None, **kv):
        if d is not None:
            if type(d) == dict:
                self.__from_dict(d)
            elif type(d) == str:
                self.__from_dict(json.loads(d))
        else:
            self.__from_dict(kv)
        
class TestStruct(TestCase):
    def test_init_kw(self):
        s = Struct(a=3, b=4)
        assert s.a == 3
        assert s.b == 4
    def test_init_dict(self):
        s = Struct(dict(b=2, x='flaz'))
        assert s.b == 2
        assert s.x == 'flaz'
    def test_init_json(self):
        s = Struct(r'{"a":3,"b":5,"c":[1,2,{"x":7,"y":6,"z":8}]}')
        assert s.a == 3
        assert len(s.c) == 3
        assert s.c[0] == 1
        assert s.c[1] == 2
        assert s.c[2].x == 7
        assert s.c[2].y == 6
        assert s.c[2].z == 8

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
        