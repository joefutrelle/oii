from threading import Lock
import os
import mimetypes
import json
import re
from datetime import timedelta

import httplib as http

from flask import Flask, Blueprint, Response, abort, request, render_template, render_template_string, redirect, current_app

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm import sessionmaker, scoped_session

from oii.times import iso8601

from oii.workflow.orm import Product, Dependency, Products
from oii.workflow.orm import STATE, NEW_STATE, EVENT, MESSAGE, TTL, UPSTREAM_STATE
from oii.workflow.orm import WAITING, AVAILABLE, ROLE, ANY, HEARTBEAT, UPSTREAM, RUNNING
from oii.workflow.async import async_config, async_wakeup

from oii.workflow.client import DEFAULT_PORT, API_PREFIX

# constants
MIME_JSON='application/json'

# configuration parameters
ASYNC_CONFIG_MODULE='ASYNC_CONFIG_MODULE'
DATABASE_URL='DATABASE_URL'

# this is a Flask blueprint
workflow_blueprint = Blueprint('workflow_blueprint',__name__)

# global ORM session object
session = None

@workflow_blueprint.before_app_first_request
def config():
    # get async config module from Flask config (i.e., WSGI config)
    async_config_module = current_app.config.get(ASYNC_CONFIG_MODULE)
    async_config(async_config_module)
    # get database configuration from Flask config
    db_url = current_app.config.get(DATABASE_URL)
    dbengine = create_engine(db_url)
    global session
    session = scoped_session(sessionmaker(bind=dbengine))()

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
    d = {
        'id': product.id,
        'pid': product.pid,
        STATE: product.state,
        EVENT: product.event,
        MESSAGE: product.message,
        TTL: product.ttl,
        'ts': iso8601(product.ts.timetuple()),
        'expires': iso8601(product.expires.timetuple()) if product.expires is not None else None
    }
    return d

def product2json(product):
    return json.dumps(product2dict(product))

############ ORM utils ################

def product_params(form,defaults):
    params = {}
    for k in [STATE, EVENT, MESSAGE, NEW_STATE, TTL, UPSTREAM_STATE]:
        params[k] = form.get(k,default=defaults.get(k,None))
    return params

def params2product(pid,params):
    return Product(pid=pid,
                   state=params.get(STATE,None),
                   event=params.get(EVENT,None),
                   message=params.get(MESSAGE,None),
                   ttl=params.get(TTL,None))

def do_create(pid,params):
    p = params2product(pid, params)
    session.add(p)
    return p

def do_update(p,params):
    p.changed(state=params[STATE],
              event=params[EVENT],
              message=params[MESSAGE],
              ttl=params[TTL])

# commit a change, and if it results in an integrity error,
# return the given HTTP error status code
def do_commit(error_code=http.INTERNAL_SERVER_ERROR):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        abort(error_code)

def product_response(p,error_code=http.NOT_FOUND,success_code=http.OK):
    if p is None:
        abort(error_code)
    else:
        return Response(product2json(p), mimetype=MIME_JSON, status=success_code)

def products_response(ps,error_code=http.NOT_FOUND,success_code=http.OK):
    if not ps or ps is None:
        abort(error_code)
    return Response(json.dumps([product2dict(p) for p in ps]), mimetype=MIME_JSON, status=success_code)

############# ENDPOINTS ##################

# create an product in a given initial state
# (default "available")
# returns a JSON representation of the product
@workflow_blueprint.route('/create/<path:pid>',methods=['GET','POST','PUT'])
def create(pid):
    params = product_params(request.form, defaults={
        STATE: AVAILABLE
    })
    p = do_create(pid, params)
    do_commit(error_code=http.CONFLICT) # commit error indicates object already exists
    return product_response(p, success_code=http.CREATED)

# delete a product regardless of its state or dependencies
@workflow_blueprint.route('/delete/<path:pid>',methods=['GET','POST','DELETE'])
def delete(pid):
    p = Products(session).get(pid)
    if p is None:
        abort(http.NOT_FOUND)
    else:
        session.delete(p)
        do_commit()
        return Response(dict(deleted=p), mimetype=MIME_JSON)

# delete a product and all its ancestors
@workflow_blueprint.route('/delete_tree/<path:pid>',methods=['GET','POST','DELETE'])
def delete_tree(pid):
    Products(session).delete_tree(pid).commit()
    return Response(dict(tree_deleted=pid), mimetype=MIME_JSON)

# change the state of an object, and record the type of
# event that this state change is associated with.
# event, state, and messages should be specified.
# if no event is specified, the default is "heartbeat".
# if no state is specified, the default is "running"
# if no message is specified, the default is None
@workflow_blueprint.route('/update/<path:pid>',methods=['POST','PATCH'])
def update(pid):
    params = product_params(request.form, defaults={
        EVENT: HEARTBEAT,
        STATE: RUNNING,
        MESSAGE: None,
        TTL: None
    })
    new_p = params2product(pid, params)
    p = Products(session).get(pid, create=new_p)
    do_update(p, params)
    do_commit()
    return product_response(p)

# assert a dependency between a downstream product and an upstream product,
# where that dependency is associated with a role that the upstream product
# plays in the production of the downstream product. the default role is 'any'.
# products are implicitly created and so form arguments are accepted for
# state, event, and message for the downstream product. any implicitly created
# upstream product is placed in the 'available' state
@workflow_blueprint.route('/depend/<path:down_pid>',methods=['POST','PUT'])
def depend(down_pid):
    try:
        up_pid = request.form[UPSTREAM]
    except KeyError:
        abort(http.BAD_REQUEST)
    role = request.form.get(ROLE,default=ANY)
    params = product_params(request.form, defaults={
        STATE: WAITING
    })
    ps = Products(session)
    dp = ps.get(down_pid, create=params2product(down_pid, params))
    up = ps.session.query(Product).filter(Product.pid==up_pid).first()
    up = ps.get(up_pid, create=params2product(up_pid, {
        STATE: AVAILABLE,
        EVENT: 'implicit_create'
    }))
    ps.add_dep(dp, up, role)
    do_commit()
    return product_response(dp)

# find all products whose upstream dependencies are all in the given state
# (default "available") for the given roles
@workflow_blueprint.route('/downstream',methods=['GET','POST'])
@workflow_blueprint.route('/downstream/<path:role_list>',methods=['GET','POST'])
def downstream(role_list=None):
    kw = product_params(request.form, defaults={
        STATE: None,
        UPSTREAM_STATE: None
    })
    if role_list:
        roles = role_list.split('/')
    else:
        roles = []
    p = Products(session).downstream(roles, kw[STATE], kw[UPSTREAM_STATE])
    return products_response(p)

# find a product whose upstream dependencies for the given roles
# are all in the given state
# (default "available") and atomically change its state to a new one
# (default "running")
@workflow_blueprint.route('/start_next/<path:role_list>',methods=['GET','POST'])
def start_next(role_list):
    kw = product_params(request.form, defaults={
        STATE: WAITING,
        UPSTREAM_STATE: AVAILABLE,
        TTL: None
    })
    roles = role_list.split('/')
    p = Products(session).start_next(roles, kw[STATE], kw[UPSTREAM_STATE], kw[TTL])
    # note that start_next commits and handles errors
    return product_response(p)

@workflow_blueprint.route('/update_if/<path:pid>',methods=['POST','PATCH'])
def update_if(pid):
    kw = product_params(request.form, defaults={
        STATE: WAITING,
        NEW_STATE: RUNNING
    })
    p = Products(session).\
        update_if(pid, state=kw[STATE], new_state=kw[NEW_STATE],
                  event=kw[EVENT], message=kw[MESSAGE], ttl=kw[TTL])
    # FIXME could the above expression be simplified with **?
    return product_response(p, error_code=http.CONFLICT)

@workflow_blueprint.route('/expire',methods=['GET','POST','DELETE'])
def expire():
    kw = product_params(request.form, defaults={
        STATE: RUNNING,
        NEW_STATE: WAITING,
        EVENT: 'expired'
    })
    n = Products(session).expire(**kw)
    if n == 0:
        abort(404)
    return Response(json.dumps(dict(expired=n)),mimetype=MIME_JSON)

@workflow_blueprint.route('/most_recent')
@workflow_blueprint.route('/most_recent/<int:n>')
def most_recent(n=25):
    return products_response(Products(session).most_recent(n))

# products and dependencies

@workflow_blueprint.route('/search/<path:frag>')
def search(frag):
    return products_response(Products(session).search(frag))

@workflow_blueprint.route('/get/<path:pid>')
def get(pid):
    return product_response(Products(session).get(pid))

@workflow_blueprint.route('/get_graph/<path:pid>')
def get_graph(pid):
    # FIXME move impl to ORM?
    p = Products(session).get(pid)
    ps = [p]
    for a in p.ancestors:
        ps.append(a)
    for d in p.descendants:
        ps.append(d)
    r = []
    for p in ps:
        for ud in p.upstream_dependencies:
            r.append(dict(downstream=p.pid, state=p.state, upstream=ud.upstream.pid, role=ud.role))
    return Response(json.dumps(r), mimetype=MIME_JSON)

# asynchronous notification support

# wake up workers optionally with a pid payload
@workflow_blueprint.route('/wakeup')
@workflow_blueprint.route('/wakeup/<path:pid>')
def wakeup(pid=None):
    async_wakeup(pid)
    return Response(json.dumps(dict(status='success')),mimetype=MIME_JSON)
