from StringIO import StringIO
import urllib2
from zipfile import ZipFile
import shutil
import sys
import os

"""Source/sink model of I/O

Sources and Sinks provide io open/close and the with statement.

For instance LocalFileSource provides read access to local file content:
foo = LocalFileSource('/tmp/foo.txt')
ins = foo.open()
contents = ins.read()
ins.close()

or

with LocalFileSource('/tmp/foo.txt') as ins:
    contents = ins.read()

"""

class Pipe(object):
    """Abstract parent class of Sinks and Sources providing with statement support
    and semantics of opening and closing"""
    def __init__(self, filelike):
        self.filelike = filelike
    def open(self):
        return self.filelike # assume it's already open
    def __enter__(self):
        self.opened = self.open()
        return self.opened
    def __exit__(self, type, value, traceback):
        self.close()
    def close(self):
        self.opened.close()
        
"""Sources"""
    
class Source(Pipe):
    pass

class LocalFileSource(Source):
    """Input comes from a local file, given a pathname"""
    def __init__(self,pathname,mode='r'):
        self.pathname = pathname
        self.mode = mode
    def open(self):
        print 'opening local file %s for reading' % self.pathname
        return open(self.pathname, self.mode)

class ByteSource(Source):
    """Input comes from a byte array"""
    def __init__(self,bytes):
        self.bytes = bytes
    def open(self):
        return StringIO(self.bytes)
        
class UrlSource(Source):
    """Input comes from an HTTP GET request"""
    def __init__(self,url):
        self.url = url
    def open(self):
        return urllib2.urlopen(self.url)
    
class LineSource(Source):
    """Wraps another source, reads lines, and extracts the desired line(s)"""
    def __init__(self,source,line_number,n=1):
        self.source = source
        self.line_number = line_number
        self.n = n
    def open(self):
        i = 0
        with self.source as input:
            o = StringIO()
            for line in input:
                if i >= self.line_number and i < self.line_number + self.n:
                    o.write(line)
                i += 1
            bs = ByteSource(o.getvalue())
            o.close()
            return bs.open()

class PartSource(Source):
    """Wraps another source, and reads a byte range of it"""
    def __init__(self,source,offset,length):
        self.source = source
        self.offset = offset
        self.length = length
    def open(self):
        try:
            with open(self.source.pathname,'rb') as raf:
                raf.seek(self.offset)
                return StringIO(raf.read(self.length))
        except:
            with self.source as source:
                source.read(self.offset)
                return StringIO(source.read(self.length))

"""Sinks"""

class Sink(Pipe):
    pass
    
class LocalFileSink(Sink):
    def __init__(self,pathname,mode=None):
        self.pathname = pathname
        self.mode = mode
    def open(self):
        if self.mode is None:
            return open(self.pathname, 'w')
        else:
            return open(self.pathname)

class OpenFileSink(Sink):
    def __init__(self,file):
        self.file = file
    def open(self):
        return self.file

class ByteSink(Sink):
    def __init__(self,handler=None):
        self.handler = handler
    def open(self):
        return StringIO()
    def close(self):
        if self.handler is not None:
            self.handler(self.opened.getvalue())
        super(Sink,self).close()

# FIXME needed: UrlSink
        
"""Utilities"""

def drain(source,sink):
    with source as input:
        with sink as output:
            shutil.copyfileobj(input, output)
    
"""Store API"""

class Store(object):
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        pass
    def __iter__(self):
        for lid in self.list():
            yield lid
    def put(self, lid, data):
        with self.sink(lid) as output:
            output.write(data)
            output.flush()
    def get(self, lid):
        with self.source(lid) as input:
            return input.read()
    def copy(self, lid, copy_lid):
        self.put(copy_lid, self.get(lid))
    def include(self, other_store):
        for lid in other_store:
            self.put(lid, other_store.get(lid))
        
class MemoryStore(Store):
    """Local ID's are arbitrary keys; values are stored in a dictionary"""
    def __init__(self):
        self.storage = {}
    def source(self, lid):
        return ByteSource(self.storage[lid])
    def sink(self, lid):
        def save(data):
            self.storage[lid] = data
        return ByteSink(save)
    def list(self):
        return self.storage.keys()

class DirectoryStore(Store):
    """Local IDs are pathnames relative to the specified directory"""
    def __init__(self,directory):
        self.directory = directory
    def source(self, lid):
        return LocalFileSource(os.path.join(self.directory, lid))
    def sink(self, lid):
        return LocalFileSink(os.path.join(self.directory, lid))
    def list(self):
        return os.listdir(self.directory)
    
class LocalFileStore(DirectoryStore):
    """Local IDs are absolute pathnames in the local filesystem"""
    def __init__(self):
        super(LocalFileStore,self).__init__('')
    
class WebStore(Store):
    """Local ID's are WWW URLs"""
    def source(self, lid):
        return UrlSource(lid)

class ZipStore(Store):
    """A store that provides read or write access to a zip archive."""
    def __init__(self,pipe,mode=None,compression=None):
        self.pipe = pipe
        self.mode = mode
        self.compression = compression
    def open(self):
        if self.mode is None:
            self.zip = ZipFile(self.pipe.open())
        elif self.compression is None:
            self.zip = ZipFile(self.pipe.open(), self.mode)
        else:
            self.zip = ZipFile(self.pipe.open(), self.mode, self.compression)
    def __enter__(self):
        self.open()
        return self
    def __exit__(self, type, value, traceback):
        self.zip.close()
    def get(self, lid):
        return self.zip.read(lid)
    def put(self, lid, data):
        self.zip.writestr(lid, data)
    def list(self):
        return self.zip.namelist()

"""Store utilities"""
