# web utils
from oii.utils import jsons
from oii.times import iso8601, parse_date_param, struct_time2utcdatetime
from flask import Response
from werkzeug.routing import BaseConverter
import re

# generate a JSON response with correct MIME type
def jsonr(whatevs):
    return Response(jsons(whatevs), mimetype='application/json')

# URL converter which "fixes" URLs that have had protocol:// converted to protocol:/
# based on example in http://werkzeug.pocoo.org/docs/routing/#custom-converters
class UrlConverter(BaseConverter):
    def __init__(self, url_map):
        super(UrlConverter, self).__init__(url_map)
        # regex cribbed in part from
        # http://stackoverflow.com/questions/6718633/python-regular-expression-again-match-url
        self.regex = '[\w\d:#@%/;$()~_?\+-=\\\.&]+'
    def to_python(self, value): # FIXME support other protocols
        return re.sub(r'(https?):/([^/])',r'\1://\2',value)
    def to_url(self, value):
        return value

# iso8601 timestamp to utc datetime
class DatetimeConverter(BaseConverter):
    def __init__(self, url_map):
        super(DatetimeConverter, self).__init__(url_map)
        self.regex = r'\d+-?\d+-?\d+([^/]+\d+:?\d+(:?\d)?)?Z?'
    def to_python(self, value):
        if value is None:
            return None
        return struct_time2utcdatetime(parse_date_param(value))
    def to_url(self, value):
        return iso8601(value.timetuple())
