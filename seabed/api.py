
from sys import stdout, stderr, exit
from os import path
from flask import Flask, abort, send_file, Response
from lxml import etree
from oii import resolver

"""
---- Simple Seabed Resolver API Prototype ----

Returns jpg images or machine-readable error codes
for requests like:
http://127.0.0.1:5000/JPGG.20040605.09303595.1499.jpg

Reads resolver config from local directory.

Written by Mark Nye, Aug 4, 2012
"""


RESOLVER_CONFIG = "seabed-resolvers.xml"
DEBUG = True


# attempt to load resolver config from local dir
configpath = path.join(path.split(path.abspath(__file__))[0]
    ,RESOLVER_CONFIG)
try:
    r = resolver.parse(configpath,"seabed_cruises")
except:
    stderr.write("error loading resolver config from %s\n" % configpath)


app = Flask(__name__)


def xml_error_response(code,msg):
    "Build XML error response"
    root = etree.Element("error") 
    error_code = etree.SubElement(root, "error_code")
    error_code.text = str(code)
    error_msg = etree.SubElement(root, "error_msg")
    error_msg.text = msg
    return Response(
        '<?xml version="1.0" ?>%s' % (etree.tostring(root)),
        status=int(code),
        mimetype='application/xml')


def validate_pid(pid):
    "minimal for now. simply checks length of string"
    if len(pid) <= 255:
        return True
    else:
        return False


# Override Flask error handlers for some common
# codes to return machine-readable errors.

@app.errorhandler(400)
def not_found(error=None):
    "overrides default flask 400"
    return xml_error_response("400","Bad Request")

@app.errorhandler(404)
def not_found(error=None):
    "overrides default flask 404"
    return xml_error_response("404","Not Found")

@app.errorhandler(500)
def not_found(error=None):
    "overrides default flask 500"
    return xml_error_response("500","Internal Server Error")

@app.errorhandler(501)
def not_found(error=None):
    "overrides default flask 501"
    return xml_error_response("501","Not Implemented")


# JPG and XML request routes

@app.route('/<pid>.jpg',methods = ['GET'])
def api_image(pid):
    "Validate, then return image or 404 response"
    if not validate_pid(pid):
        abort(400)
    for (hit,bindings) in resolver.resolve(r, dict(pid=pid)):
        # assume unique names, return first image hit 
        try:
            return send_file(hit,mimetype="image/jpeg",cache_timeout=60)
        except IOError:
            """Permission or filesystem problem fetching image.
            This should be logged in production. For now, return 500."""
            abort(500)
    else:
        abort(404)

@app.route('/<pid>.xml',methods = ['GET'])
def api_xml(pid):
    "This is coming later. For now return 501."
    abort(501)


if __name__ == '__main__':
    "Are we in the __main__ scope? Start test server."
    app.run(host='127.0.0.1',port=5000,debug=DEBUG) 
