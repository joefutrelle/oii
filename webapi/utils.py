# web utils
from oii.utils import jsons
from flask import Response

# generate a JSON response with correct MIME type
def jsonr(whatevs):
    return Response(jsons(whatevs), mimetype='application/json')