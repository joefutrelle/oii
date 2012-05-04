"""Source/sink model of I/O"""
from StringIO import StringIO
import urllib2
from zipfile import ZipFile
import shutil
import sys
import os

class SourceSink(object):
    """Abstract parent class of Sinks and Sources providing with statement support
    and semantics of opening and closing"""
    def __enter__(self):
        self.opened = self.open()
        return self.opened
    def __exit__(self, type, value, traceback):
        self.close()
    def close(self):
        self.opened.close()
        
"""Sources"""
    
class Source(SourceSink):
    """Abstract parent class of sources providing read method"""
    def read(self):
        with self as input:
            return input.read()

class LocalFileSource(Source):
    """Input comes from a local file, given a pathname"""
    def __init__(self,pathname,mode='r'):
        self.pathname = pathname
        self.mode = mode
    def open(self):
        return open(self.pathname, self.mode)

class OpenFileSource(Source):
    """Input comes from an open file-like object. Note that __exit__ will not close this object"""
    def __init__(self,file):
        self.file = file
    def open(self):
        return self.file
    def close(self):
        pass
    
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

"""Sinks"""

class Sink(SourceSink):
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
    def put(self, lid, data):
        with self.sink(lid) as output:
            output.write(data)
            output.flush()
    def get(self, lid):
        with self.source(lid) as input:
            return input.read()
        
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

class ReadonlyZipStore(Store):
    """A store providing store read operations on a zip source."""
    def __init__(self,source,mode=None):
        self.source = source
        self.mode = mode
    def open(self):
        if self.mode is None:
            self.opened = ZipFile(self.source.open())
        else:
            self.opened = ZipFile(self.source.open(), self.mode)
        return self
    def close(self):
        self.opened.close()
    def __enter__(self):
        return self.open()
    def __exit__(self, type, value, traceback):
        self.close()
    def list(self):
        return self.opened.namelist()
    def get(self, lid):
        self.opened.read(lid)

class ZipStore(ReadonlyZipStore):
    """A store that provides read or write access to a zip archive. Note that write access
    requires that the source be a LocalFileSink, and mode to be 'w'"""
    def __init__(self,source,mode=None):
        super(ZipStore,self).__init__(source,mode)
    def open(self):
        try:
            if self.mode is None:
                self.opened = ZipFile(self.source.pathname)
            else:
                self.opened = ZipFile(self.source.pathname, self.mode)
            return self
        except KeyError:
            return super(ZipStore,self).open()
    def put(self, lid, data):
        self.opened.writestr(lid, data)

        