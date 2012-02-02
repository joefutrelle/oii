import time
import calendar
from unittest import TestCase

"""Utilities for working with timestamps"""

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
RFC_822_FORMAT = '%a, %d %b %Y %H:%M:%S +0000'

def local_to_utc(t=time.localtime()):
    """Make sure that the dst flag is -1 -- this tells mktime to take daylight
    savings into account"""
    secs = time.mktime(t)
    return time.gmtime(secs)

def utc_to_local(t=time.gmtime()):
    secs = calendar.timegm(t)
    return time.localtime(secs)

def iso8601(t=time.gmtime()):
    return time.strftime(ISO_8601_FORMAT,t)

def rfc822(t=time.gmtime()):
    return time.strftime(RFC_822_FORMAT,t)

class test_formats(TestCase):
    def runTest(self):
        assert iso8601(time.gmtime(0)) == '1970-01-01T00:00:00Z'
        assert iso8601(time.gmtime(1328203363)) == '2012-02-02T17:22:43Z'
        assert rfc822(time.gmtime(0)) == 'Thu, 01 Jan 1970 00:00:00 +0000'
        assert rfc822(time.gmtime(1328203363)) == 'Thu, 02 Feb 2012 17:22:43 +0000'

