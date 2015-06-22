# utilities for oii
from threading import Lock
import os
import re
from hashlib import sha1
import time
from functools import wraps
from unittest import TestCase
import json
from subprocess import Popen, PIPE
import platform
import ctypes
import hashlib
import sys
from datetime import timedelta
from multiprocessing import Pool
from types import GeneratorType
from shutil import copyfileobj, rmtree
from tempfile import mkdtemp
from contextlib import contextmanager

genid_prev_id_tl = Lock()
genid_prev_id = None

def coalesce(*args):
    """return first non-None arg or None if none"""
    for arg in args:
        if arg is not None:
            return arg
    return None

def search_path(pathname_suffix):
    """search the python path for a pathname relative to it"""
    cands = [os.path.join(d,pathname_suffix) for d in sys.path]
    try:
        return filter(os.path.exists, cands)[0]
    except IndexError:
        return None

# from http://stackoverflow.com/questions/653368/how-to-create-a-python-decorator-that-can-be-used-either-with-or-without-paramet
def doublewrap(f):
    '''
    a decorator decorator, allowing the decorator to be used as:
    @decorator(with, arguments, and=kwargs)
    or
    @decorator
    '''
    @wraps(f)
    def new_dec(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # actual decorated function
            return f(args[0])
        else:
            # decorator arguments
            return lambda realf: f(realf, *args, **kwargs)
    return new_dec

@doublewrap
def memoize(fn,ttl=31557600,ignore_exceptions=False,key=None):
    """decorator to memoize a function by its args,
    with an expiration time. use this to wrap an idempotent
    or otherwise cacheable getter or transformation function.
    the function args must be hashable.
    ignore exceptions means not to expire values in the case
    that the function to generate them raises an exception.
    if a generator is received, silently applies list() to it.
    be very careful about memoizing generator functions as this
    may not be desired"""
    cache = {}
    exp = {}
    @wraps(fn)
    def inner(*args,**kw):
        now = time.time()
        if key is not None:
            args_key = key(args)
        else:
            args_key = args
        if args_key not in exp or now > exp[args_key] or args_key not in cache:
            try:
                new_value = fn(*args,**kw)
            except:
                if ignore_exceptions and args_key in cache:
                    new_value = cache[args_key]
                else:
                    raise
            # we've got a value to cache, but it's a generator; freeze it
            if isinstance(new_value, GeneratorType):
                new_value = list(new_value)
            cache[args_key] = new_value
            exp[args_key] = now + ttl
        return cache[args_key]
    return inner

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry

def sizeof_fmt(num, suffix='B'):
    """format a bytecount for human-readability.
    by Fred Cirera, see 
    http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def gen_id(namespace=''):
    """generate a unique global identifier"""
    global genid_prev_id
    with genid_prev_id_tl:
        prev = genid_prev_id
        if prev is None:
            prev = sha1(os.urandom(24)).hexdigest()
        else:
            entropy = str(time.clock()) + str(time.time()) + str(os.getpid())
            prev = sha1(prev + entropy).hexdigest()
        genid_prev_id = prev
    return namespace + prev

@contextmanager
def safe_tempdir(suffix='', prefix='tmp', dir=None):
    try:
        tempdir = mkdtemp(suffix,prefix,dir)
        yield tempdir
    finally:
        rmtree(tempdir)

def safe_copy(src_path, dest_path):
    """copy a file to another location as atomically as possible"""
    dest_dir = os.path.dirname(dest_path)
    # ensure directory exists
    try:
        os.makedirs(dest_dir)
    except:
        pass
    if not os.path.isdir(dest_dir):
        # well, making the directory didn't work
        raise IOError('unable to create directory %s' % dest_dir)
    tmp_fn = os.path.join(dest_dir,gen_id())
    def safe_remove_tmp():
        try:
            os.remove(tmp_fn)
        except:
            pass
    try:
        with open(src_path,'rb') as src_fo:
            with open(tmp_fn,'wb') as dest_fo:
                copyfileobj(src_fo,dest_fo)
        os.rename(tmp_fn,dest_path)
    except:
        safe_remove_tmp()
        raise
    finally:
        safe_remove_tmp()

def compare_files(src,dest,name=True,size=False,checksum=False):
    """compare two files to make sure theyre the same. checks include:
    - name: file names (not any of the rest of the paths) match
    - size: sizes match
    - checksum: checksums match (warning! slow for large files)
    automatically checks that both exist.
    return True on successful match, False otherwise"""
    if not os.path.isfile(src):
        return False
    if not os.path.isfile(dest):
        return False
    if name:
        src_name = os.path.basename(src)
        dest_name = os.path.basename(dest)
        if not src_name == dest_name:
            return False
    if size:
        src_size = os.stat(src).st_size
        dest_size = os.stat(dest).st_size
        if src_size != dest_size:
            return False
    if checksum:
        src_checksum = sha1_file(src)
        dest_checksum = sha1_file(dest)
        if src_checksum != dest_checksum:
            return False
    return True
        
def scatter(fn,argses,callback=None,processes=None):
    """Extremely simple multiprocessing.
    Parameters:
    fn - the function to apply
    argses - a list of argument lists for that function
    callback (optional) - a callback to receive results.
    processes (optional) - how many simultaneous processes to run."""
    pool = Pool(processes=processes)
    for args in argses:
        pool.apply_async(fn,args,{},callback)
    pool.close()
    pool.join()

# order the keys of a dict according to a sequence
# any keys in the sequence that are not present in the dict will not be listed
# any keys in the dict that are not in the sequence will be listed in alpha order
def order_keys(d,s):
    sk = [key for key in s if key in d.keys()]
    dk = sorted([key for key in d.keys() if key not in s])
    return sk + dk

# convert camelCase to Title Case
def decamel(s):
    return string.capwords(re.sub(r'([a-z])([A-Z]+)',r'\1 \2',s))

def remove_extension(p):
    """remove extension part of filename"""
    return re.sub(r'\.[a-zA-Z][a-zA-Z0-9]*$','',p)

def change_extension(p,ext):
    """modify extension part of filename"""
    return remove_extension(p) + '.%s' % ext

def sha1_string(data):
    """Compute the SHA-1 hash of a string"""
    m = hashlib.sha1()
    m.update(data)
    return m.hexdigest()

def sha1_filelike(filelike):
    """Compute the SHA-1 hash of a file-like object"""
    m = hashlib.sha1()
    while True:
        s = filelike.read()
        if len(s) == 0:
            break
        else:
            m.update(s)
    return m.hexdigest()

def sha1_file(pathname):
    """Compute the SHA-1 hash of a file at a pathname"""
    with open(pathname,'rb') as fl:
        return sha1_filelike(fl)

def md5_string(data):
    """Compute the MD5 hash of a string"""
    m = hashlib.md5()
    m.update(data)
    return m.hexdigest()

def md5_filelike(filelike):
    """Compute the MD5 hash of a file-like object"""
    m = hashlib.md5()
    while True:
        s = filelike.read()
        if len(s) == 0:
            break
        else:
            m.update(s)
    return m.hexdigest()

def md5_file(pathname):
    """Compute the MD5 hash of a file at a pathname"""
    with open(pathname,'rb') as fl:
        return md5_filelike(fl)

def relocate(path,new_dir,new_extension=None):
    new_basename = os.path.basename(path)
    if new_extension is not None:
        new_basename = change_extension(os.path.basename(path),new_extension)
    return os.path.join(new_dir, new_basename)

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
    
    def __init__(self, d={}):
        for k,v in d.items():
            self.__dict__[k] = structs(v)

__none = object()

def dict_slice(d,schema,default=__none):
    """d - a dict to slice
    keys - the keys to slice, or if a dict, a dict mapping those keys to functions to call on the values first."""
    try: # allow schema to be a string in the form x,y,z
        schema = re.split(',',schema)
    except TypeError: 
        pass
    try: # allow schema to be a dict mapping keys to functions
        if default != __none:
            xf = dict(zip(schema.keys(),[default for _ in schema.keys()]))
        else:
            xf = {}
        xf.update(dict((k,v) for k,v in d.iteritems() if k in schema.keys()))
        xf.update(dict((k,schema[k](xf[k])) for k in schema.keys() if schema[k] is not None))
        xf.update(dict((k,d[k]) for k in schema.keys() if schema[k] is None))
        return xf
    except: # ok, schema must be a sequence of keys
        if default != __none:
            xf = dict(zip(schema,[default for _ in schema]))
        else:
            xf = {}
        xf.update(dict((k,v) for k,v in d.iteritems() if k in schema))
        return xf

def dict_rename(d,keymap):
    r = {}
    for k1,k2 in keymap.items():
        r[k2] = d[k1]
    return r
 
# simple storage API allows for storing structures with random access by a key field
# and listing by a key/value template
# default impl fronts a dict
class SimpleStore(object):
    # either use a dict key or function to extract keys from items
    def __init__(self,key=None):
        if type(key) is str:
            self.key_fn = lambda s: s[key]
        elif key is not None:
            self.key_fn = key
        self.db = {}
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

def freespace(pth):
    """
    Return folder/drive free space (in bytes)
    from http://stackoverflow.com/questions/51658/cross-platform-space-remaining-on-volume-using-python
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        s = os.statvfs(pth)
        return s.f_frsize * s.f_bavail

def rpad(s,l,pad_string=' '):
    return s + (pad_string * (l - len(s)))

def asciitable(dicts,disp_cols=None,none_msg=None,border=True):
    """produce an ASCII formatted columnar table from the dicts"""
    dicts = list(dicts)
    if not dicts:
        if none_msg is not None:
            yield none_msg
        return
    if disp_cols is not None:
        cols = disp_cols
    else:
        # set of all keys in dicts
        cols = sorted(list(set(reduce(lambda x,y: x+y, [d.keys() for d in dicts]))))
    # compute col widths. initially wide enough for the column label
    widths = dict([(col,len(col)) for col in cols])
    # now create rows, and in doing so compute max width of each column
    for row in list(dicts):
        for col in cols:
            try:
                width = len(str(row[col]))
            except KeyError:
                width = 0
            if width > widths[col]:
                widths[col] = width
    def bord(line,border_char='|',pad_char=' '):
        if border:
            return border_char + pad_char + line + pad_char + border_char
        else:
            return line
    # now print rows
    spacer = bord('-+-'.join(['-' * widths[col] for col in cols]),'+','-')
    if border:
        yield spacer
    yield bord(' | '.join([rpad(col,widths[col]) for col in cols]),'|')
    yield spacer
    for row in dicts:
        yield bord(' | '.join([rpad(str(row[col]),widths[col]) for col in cols]),'|')
    if border:
        yield spacer
    
### tests

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

class TestDestructs(TestCase):
    def test_str(self):
        assert destructs('foo') == 'foo'
    def test_struct(self):
        assert destructs(structs({'a':3})) == {'a':3}
    def test_dict(self):
        d = destructs(structs({'a':{'b':3}}))
        assert d['a']['b'] == 3
        assert destructs(structs([{'a':3}]))[0]['a']
        
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
        d = dict(a=3, b=7, c=8)
        m = dict(a=lambda x: x+2, b=str)
        s = dict_slice(d,m)
        assert s == dict(a=5,b='7')
    def test_list_default(self):
        d = dict(a=3, b=7, c=8)
        k = ['a','c','d']
        s = dict_slice(d,k,default=None)
        assert s == dict(a=3, c=8, d=None)
    def test_str_default(self):
        d = dict(a=3, b=7, c=8)
        k = ['a','c','d']
        s = dict_slice(d,k,'qunk')
        assert s == dict(a=3, c=8, d='qunk')
    def test_map_default(self):
        d = dict(a=3, b=7, c=8)
        m = dict(a=lambda x: x+2, b=str, d=lambda x: x+100)
        s = dict_slice(d,m,20)
        assert s == dict(a=5,b='7',d=120)
        
class TestMapr(TestCase):
    def runTest(self):
        ins = {"a": 3, "c": [1, 2, {"y": 6, "x": 7, "z": 8}], "b": 5}
        outs = {"a": '3', "c": ['1', '2', {"y": '6', "x": '7', "z": '8'}], "b": '5'}
        assert mapr(str,ins) == outs
        
class TestSimpleStore(TestCase):
    def test_dk(self):
        dk = 'foo'
        store = SimpleStore(dk)
        d = dict(foo='quonk', bar='z')
        store.add(d)
        assert store.fetch('quonk') == d
