# utilities for oii
from threading import Lock
import os
import re
from hashlib import sha1
from time import time, clock
from unittest import TestCase
import json

genid_prev_id_tl = Lock()
genid_prev_id = None

def gen_id(namespace=''):
    global genid_prev_id
    with genid_prev_id_tl:
        prev = genid_prev_id
        if prev is None:
            prev = sha1(os.urandom(24)).hexdigest()
        else:
            entropy = str(clock()) + str(time()) + str(os.getpid())
            prev = sha1(prev + entropy).hexdigest()
        genid_prev_id = prev
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

class TestStructs(TestCase):
    def test_str(self):
        item = 'foo'
        assert structs(item) == 'foo'
    def test_dict(self):
        item = dict(a=3, b=7)
        assert structs(item).a == 3
        assert structs(item).b == 7
        item = structs({'a':{'b':2}})
        assert item.a.b == 2
        item = structs([{'a':3}])
        assert item[0].a == 3
    def test_seq(self):
        item = [1,2,3]
        assert structs(item) == [1,2,3]
        item = [1,{'a':3},3]
        assert structs(item)[1].a == 3
    def test_int(self):
        item = 2
        assert structs(item) == 2
        
def destructs(item):
    if isinstance(item,basestring):
        return item
    try:
        return item.destruct
    except:
        pass
    try:
        return dict([(k,destructs(v)) for k,v in item.iteritems()])
    except:
        pass
    try:
        return map(destructs,item)
    except:
        pass
    return item

class TestDestructs(TestCase):
    def test_str(self):
        assert destructs('foo') == 'foo'
    def test_struct(self):
        assert destructs(structs({'a':3})) == {'a':3}
    def test_dict(self):
        d = destructs(structs({'a':{'b':3}}))
        assert d['a']['b'] == 3
        assert destructs(structs([{'a':3}]))[0]['a']

# external, accepts Structs, sequences, or primitive values
def jsons(item):
    return json.dumps(destructs(item))

class Struct():
    @property
    def destruct(self):
        result = {}
        for k,v in self.__dict__.iteritems():
            try:
                result[k] = v.destruct
            except AttributeError:
                # handle lists and tuples separately, so no duck typing
                if isinstance(v,list):
                    result[k] = map(lambda e: e.destruct if isinstance(e,Struct) else e, v)
                elif isinstance(v,tuple):
                    result[k] = tuple(map(lambda e: e.destruct if isinstance(e,Struct) else e,v))
                else:
                    result[k] = v
        return result
    
    @property
    def json(self):
        return json.dumps(self.destruct)
    
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
        
# simple storage API allows for storing structures with random access by a key field
# and listing by a key/value template
# default impl fronts a dict
class SimpleStore(object):
    key_fn = lambda s: s
    db = {}
    # either use a dict key or function to extract keys from items
    def __init__(self,key=None):
        if type(key) is str:
            self.key_fn = lambda s: s[key]
        elif key is not None:
            self.key_fn = key
    # add single item
    def add(self,s):
        self.db[self.key_fn(s)] = s
    # add multiple items
    def addEach(self,seq):
        for s in seq:
            self.add(s)
    # remove item with a given key
    def removeKey(self,key):
        del self.db[key]
    # fetch item by key
    def fetch(self,key):
        return self.db[key]
    # list all items matching a template item
    # any k/v's that appear in the template item must match any candidate
    def list(self,**template): 
        def template_match(d,t):
            for k,v in d.iteritems():
                if k in t and t[k] != v:
                    return False
            return True
        for s in self.db.itervalues():
            if template_match(s,template):
                yield s

class TestSimpleStore(TestCase):
    def test_dk(self):
        dk = 'foo'
        store = SimpleStore(dk)
        d = dict(foo='quonk', bar='z')
        store.add(d)
        assert store.fetch('quonk') == d
