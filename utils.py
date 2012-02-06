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

# recursively map a function onto an item. if the item is a sequence,
# descend into each item; if it's a dict, descend into each value.
def mapr(function,item):
    if isinstance(item,basestring):
        return function(item) # don't sequence-map on strings!
    try:
        return dict([(k,mapr(function,v)) for k,v in item.iteritems()])
    except:
        pass
    try:
        return map(lambda i: mapr(function,i),item)
    except:
        pass
    try:
        return function(item)
    except:
        pass
    # function won't accept, pass through
    return item

# due to http://stackoverflow.com/a/1305663
# with enhancements. Struct class provides view of JSON or JSON-like structure that allows
# direct member access. So a JSON structure {"foo":["bar":{"baz":7}]}
# could be accessed like ref.foo[0].baz

# not using jsonpickle because we only want to serialize stuff that originated in JSON
# or JSON-like structures.


class TestMapr(TestCase):
    def runTest(self):
        ins = {"a": 3, "c": [1, 2, {"y": 6, "x": 7, "z": 8}], "b": 5}
        outs = {"a": '3', "c": ['1', '2', {"y": '6', "x": '7', "z": '8'}], "b": '5'}
        assert mapr(str,ins) == outs
        
# factory method
# internal, does not interpret strings as JSON
def __struct_wrap(item):
    if isinstance(item,basestring):
        return item
    try: # assume dict
        return Struct(item)
    except:
        pass
    try: # assume sequence
        return map(__struct_wrap,item)
    except TypeError:
        return item

# external, accepts JSON strings, sequences, dicts, and keyword args
def structs(item=None,**kv):
    if item is None:
        return __struct_wrap(kv)
    try:
        return __struct_wrap(json.loads(item))
    except:
        pass
    return __struct_wrap(item)

def destructs(item):
    if isinstance(item,basestring):
        return item
    try:
        return item.as_dict
    except:
        pass
    try:
        return map(destructs,item)
    except:
        pass
    return item
    
# external, accepts Structs, sequences, or primitive values
def jsons(item):
    try:
        return map(jsons,item)
    except TypeError:
        pass
    try:
        return item.json
    except AttributeError:
        return item
    
class Struct():
    @property
    def as_dict(self):
        result = {}
        for k,v in self.__dict__.iteritems():
            try:
                result[k] = v.as_dict
            except AttributeError:
                pass
            # handle lists and tuples separately, so no duck typing
            if isinstance(v,list):
                result[k] = map(lambda e: e.as_dict if isinstance(e,Struct) else e, v)
            elif isinstance(v,tuple):
                result[k] = tuple(map(lambda e: e.as_dict if isinstance(e,Struct) else e,v))
            else:
                result[k] = v
        return result
    
    @property
    def json(self):
        return json.dumps(self.as_dict)
    
    def __repr__(self):
        return self.json
    
    def __init__(self, d):
        for k,v in d.items():
            self.__dict__[k] = structs(v)
        
class TestStruct(TestCase):
    def test_init_kw(self):
        s = structs(a=3, b=4)
        assert s.a == 3
        assert s.b == 4
    def test_init_dict(self):
        s = structs(dict(b=2, x='flaz'))
        assert s.b == 2
        assert s.x == 'flaz'
    def test_init_json(self):
        s = structs(r'{"a":3,"b":5,"c":[1,2,{"x":7,"y":6,"z":8}]}')
        assert s.a == 3
        assert len(s.c) == 3
        assert s.c[0] == 1
        assert s.c[1] == 2
        assert s.c[2].x == 7
        assert s.c[2].y == 6
        assert s.c[2].z == 8

def dict_slice(d,schema,fn=None):
    """d - a dict to slice
    keys - the keys to slice, or if a dict, a dict mapping those keys to functions to call on the values first."""
    try: # allow schema to be a string in the form x,y,z
        schema = re.split(',',schema)
    except TypeError: 
        pass
    try: # allow schema to be a dict mapping keys to functions
        xf = dict((k,schema[k](d[k])) for k in schema.keys() if schema[k] is not None)
        xf.update(dict((k,d[k]) for k in schema.keys() if schema[k] is None))
        return xf
    except: # ok, schema must be a sequence of keys
        return dict((k,v) for k,v in d.iteritems() if k in schema)
    
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
        