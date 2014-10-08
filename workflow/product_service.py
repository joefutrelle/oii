import os
import mimetypes
import json
import re

from flask import Flask, Response, abort, request, render_template, render_template_string, redirect

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oii.times import iso8601

from oii.workflow.product_orm import Base, Product, Dependency, Products

# constants

MIME_JSON='application/json'

# eventually the session cofiguration should
# go in its own class.
#SQLITE_URL='sqlite:///home/ubuntu/dev/ifcb_admin.db'
SQLITE_URL='sqlite:///product_service_test.db'

from sqlalchemy.pool import StaticPool
dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                         echo=False)
Session = sessionmaker(bind=dbengine)
session = Session()

STATIC='/static/'
app = Flask(__name__)

### generic flask utils ###
def parse_params(path, **defaults):
    """Parse a path fragment and convert to dict.
    Slashes separate alternating keys and values.
    For example /a/3/b/5 -> { 'a': '3', 'b': '5' }.
    Any keys not present get default values from **defaults"""
    parts = re.split('/',path)
    d = dict(zip(parts[:-1:2], parts[1::2]))
    for k,v in defaults.items():
        if k not in d:
            d[k] = v
    return d

def max_age(ttl=None):
    if ttl is None:
        return {}
    else:
        return {'Cache-control': 'max-age=%d' % ttl}

def template_response(template, mimetype=None, ttl=None, **kw):
    if mimetype is None:
        (mimetype, _) = mimetypes.guess_type(template)
    if mimetype is None:
        mimetype = 'application/octet-stream'
    return Response(render_template(template,**kw), mimetype=mimetype, headers=max_age(ttl))

###### representation ######
def product2dict(product):
    return {
        'id': product.id,
        'pid': product.pid,
        'state': product.state,
        'event': product.event,
        'message': product.message,
        'ts': iso8601(product.ts.timetuple())
    }

def product2json(product):
    return json.dumps(product2dict(product))

############# ENDPOINTS ##################

# create an product in a given initial state
# (default "available")
# returns a JSON representation of the product
@app.route('/create/<path:pid>',methods=['GET','POST'])
def create(pid):
    state = request.form.get('state',default='available')
    p = Product(state=state, pid=pid)
    session.add(p)
    session.commit()
    return Response(product2json(p), mimetype=MIME_JSON)

# change the state of an object, and record the type of
# event that this state change is associated with.
# if no event is specified, the default is "heartbeat".
# if no state is specified, the default is "updated".
@app.route('/update/<path:pid>',methods=['POST'])
def changed(pid):
    event = request.form.get('event',default='heartbeat')
    new_state = request.form.get('state',default='updated')
    try:
        p = session.query(Product).filter(Product.pid==pid).first()
    except:
        abort(404)
    p.changed(event, new_state)
    session.commit()
    return Response(product2json(p), mimetype=MIME_JSON)

# assert a dependency between a downstream product and an upstream product,
# where that dependency is associated with a role that the upstream product
# plays in the production of the downstream product. the default role is 'any'.
# products must already have been created with 'create'--they are not implicitly
# created
@app.route('/depend/<path:down_pid>',methods=['POST'])
def depend(down_pid):
    try:
        up_pid = request.form['upstream']
    except KeyError:
        abort(400)
    role = request.form.get('role',default='any')
    try:
        dp = session.query(Product).filter(Product.pid==down_pid).first()
        up = session.query(Product).filter(Product.pid==up_pid).first()
    except:
        abort(404)
    Products(session).add_dep(dp, up, role)
    session.commit()
    return Response(product2json(dp), mimetype=MIME_JSON) # FIXME

# find a product whose upstream dependencies are all in the given state
# (default "available") and atomically change its state to a new one
# (default "running")
# FIXME allow POST to specify state
@app.route('/start_next/<path:role_list>',methods=['GET','POST'])
def start_next(role_list):
    roles = role_list.split('/')
    p = Products(session).start_next(roles)
    if p is None:
        abort(404)
    else:
        return Response(product2json(p), mimetype=MIME_JSON)

if __name__ == '__main__':
    Base.metadata.create_all(dbengine)
    app.run(host='0.0.0.0',port=8080,debug=True)
