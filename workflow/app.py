from flask import Flask

from oii.workflow.orm import Base
from oii.workflow.client import API_PREFIX, DEFAULT_PORT
from oii.workflow.webapi import workflow_blueprint, dbengine

app = Flask(__name__)
app.register_blueprint(workflow_blueprint, url_prefix=API_PREFIX)
app.debug=True # FIXME

if __name__ == '__main__':
    Base.metadata.create_all(dbengine)
    app.run(host='0.0.0.0',port=DEFAULT_PORT,debug=True)
