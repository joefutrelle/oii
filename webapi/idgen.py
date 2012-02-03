from flask import Blueprint
from oii.utils import gen_id
import json

# this blueprint provides the /generate_ids endpoint for an app

# for various reasons we can't call the blueprint instance, the function, and the source file
# all the same thing: "generate_ids". So we have three names:
# module: idgen
# blueprint: idgen_api
# function: generate_ids
# so the url_for call is url_for('idgen_api.generate_ids')

idgen_api = Blueprint('idgen_api', __name__)

@idgen_api.route('/generate_ids/<int:n>')
@idgen_api.route('/generate_ids/<int:n>/<path:ns>')
def generate_ids(n,ns=''):
    return json.dumps([ns + gen_id() for _ in range(n)])