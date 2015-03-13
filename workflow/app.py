from flask import Flask

from oii.workflow.orm import Base
from oii.workflow.client import API_PREFIX, DEFAULT_PORT
from oii.workflow.webapi import workflow_blueprint

from oii.webapi.utils import UrlConverter

app = Flask(__name__)
# url parameter type
app.url_map.converters['url'] = UrlConverter

app.register_blueprint(workflow_blueprint, url_prefix=API_PREFIX)
app.debug=True # FIXME

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=DEFAULT_PORT,debug=True)
