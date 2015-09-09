
import os, inspect
import mimetypes
import json
from time import strptime
from io import BytesIO
import re
import PIL
import shutil
from oii.utils import gen_id
from array import array
from zipfile import ZipFile
from lxml import html
from StringIO import StringIO
from datetime import timedelta

from flask import Response, abort, request, render_template, current_app
from flask import render_template_string, redirect, send_from_directory

from sqlalchemy import and_

import numpy as np

from skimage.segmentation import find_boundaries

from oii.utils import coalesce, memoize
from oii.times import iso8601, parse_date_param, struct_time2utcdatetime, utcdtnow
from oii.image.io import as_bytes, as_pil
from oii.image import mosaic
from oii.image.mosaic import Tile

from oii.ifcb2.workflow import BINZIP_PRODUCT
from oii.workflow.client import WorkflowClient

# FIXME this is used for old PIL-based mosaic compositing API
from oii.image.pilutils import filename2format, thumbnail

from oii.ifcb2 import get_resolver
from oii.ifcb2 import files
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User, Role, UserRoles

from oii.rbac.admin_api import timeseries_blueprint, manager_blueprint
from oii.rbac.admin_api import role_blueprint, user_blueprint, password_blueprint, user_admin_blueprint
from oii.rbac.admin_api import instrument_blueprint, keychain_blueprint
from oii.rbac import security
from oii.rbac.security import roles_required

from oii.ifcb2.feed import Feed
from oii.ifcb2.formats.adc import Adc

from oii.ifcb2.files import parsed_pid2fileset, NotFound
from oii.ifcb2.accession import Accession
from oii.ifcb2.identifiers import add_pids, add_pid, canonicalize, BIN_KEY
from oii.ifcb2.represent import split_hdr, targets2csv, bin2xml, bin2json, bin2rdf, bin2zip, target2xml, target2rdf, bin2json_short, bin2json_medium, class_scoresmat2csv
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.hdr import parse_hdr_file
# keys
from oii.ifcb2.identifiers import PID, LID, ADC_COLS, SCHEMA_VERSION, TIMESTAMP, TIMESTAMP_FORMAT, PRODUCT
from oii.ifcb2.formats.adc import HEIGHT, WIDTH, TARGET_NUMBER
from oii.ifcb2.stitching import STITCHED, PAIR, list_stitched_targets, stitch_raw
from oii.ifcb2 import v1_stitching

from oii.ifcb2.dashboard.flasksetup import app
from oii.ifcb2.dashboard.flasksetup import session, dbengine, user_manager

from oii.csvio import read_csv, NO_LIMIT
from oii.iopipes import LocalFileSource

# constants
MIME_JSON='application/json'
STATIC='/static/'
ADMIN_APP_DIR = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(
    inspect.currentframe()))),'../../rbac/admin')

# config params
DASHBOARD_BASE_URL='DASHBOARD_BASE_URL'
DATABASE_URL='DATABASE_URL'
WORKFLOW_URL='WORKFLOW_URL'
# configured object keys
DBENGINE='DBENGINE'
SCOPED_SESSION='SCOPED_SESSION'
SESSION='SESSION'

# configuration
workflow_client = None
session = None

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

def init_database(dbengine, session):
    """initialize database"""
    Base.metadata.create_all(dbengine)
    session.expire_all()
    # init roles and test users
    # this should go somewhere else later
    for role in ['Admin','Instrument','Time Series', 'API']:
        if not session.query(Role).filter_by(name=role).count():
            r = Role(name=role)
            session.add(r)
            session.commit()
    if not session.query(User).filter_by(email='admin@whoi.edu').count():
        u = User(
            first_name='Test', last_name='Admin',
            email='admin@whoi.edu', username='admin@whoi.edu',
            password=user_manager.hash_password('12345678'),
            is_enabled=True)
        r = session.query(Role).filter_by(name='Admin').first()
        u.roles.append(r)
        session.add(u)
        session.commit()
    if not session.query(User).filter_by(email='user@whoi.edu').count():
        u = User(
            first_name='Test', last_name='User',
            email='user@whoi.edu', username='user@whoi.edu',
            password=user_manager.hash_password('12345678'),
            is_enabled=True)
        session.add(u)
        session.commit()

@app.before_first_request
def dashboard_config():
    # configure workflow client
    global workflow_client
    workflow_url = current_app.config.get(WORKFLOW_URL)
    workflow_client = WorkflowClient(workflow_url)
    # configure database session
    global session
    db_url = current_app.config.get(DATABASE_URL)
    dbengine = create_engine(db_url)
    ScopedSession = scoped_session(sessionmaker(bind=dbengine))
    session = ScopedSession()
    init_database(dbengine,session)
    current_app.config.update(
        DBENGINE=dbengine,
        SCOPED_SESSION=ScopedSession,
        SESSION=session
    )
    # instrument RBAC
    User.query = ScopedSession.query_property()
    Role.query = ScopedSession.query_property()
    UserRoles.query = ScopedSession.query_property()

def get_url_root():
    return current_app.config.get(DASHBOARD_BASE_URL, request.url_root)

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

#### generic IFCB utils #####
# FIXME refactor!

def ifcb():
    return get_resolver().ifcb

@memoize(ttl=30)
def parse_pid(pid):
    try:
        return next(ifcb().pid(pid))
    except StopIteration:
        raise

@memoize(ttl=30)
def get_data_roots(ts_label, product_type='raw'):
    return files.get_data_roots(session, ts_label, product_type)

def get_timestamp(parsed_pid):
    return iso8601(strptime(parsed_pid[TIMESTAMP], parsed_pid[TIMESTAMP_FORMAT]))

def get_unstitched_targets(adc, bin_pid):
    us_targets = add_pids(adc.get_targets(),bin_pid)
    for us_target in us_targets:
        # claim all are unstitched
        us_target[STITCHED] = False
        yield us_target

def get_targets(adc, bin_pid, stitched=True):
    us_targets = list(get_unstitched_targets(adc, bin_pid))
    if stitched:
        return list_stitched_targets(us_targets)
    else:
        return us_targets

@memoize(ttl=30,key=lambda args: frozenset(args[0].items()))
def get_fileset(parsed):
    time_series = parsed['ts_label']
    data_roots = list(get_data_roots(time_series))
    return parsed_pid2fileset(parsed,data_roots)

@memoize(ttl=30,key=lambda args: frozenset(args[0].items() + [args[1]]))
def get_product_file(parsed, product_type):
    parsed = dict(parsed.items())
    time_series = parsed['ts_label']
    data_roots = list(get_data_roots(time_series,product_type))
    parsed['product'] = product_type
    for root in data_roots:
        try:
            hit = next(get_resolver().ifcb.files.find_product(root=root,**parsed))
            return hit['product_path']
        except StopIteration:
            pass
    raise NotFound

def serve_blob_bin(parsed):
    blob_zip = get_product_file(parsed, 'blobs')
    return Response(file(blob_zip), direct_passthrough=True, mimetype='application/zip')

def serve_features_bin(parsed):
    feature_csv = get_product_file(parsed, 'features')
    return Response(file(feature_csv), direct_passthrough=True, mimetype='text/csv')

def serve_class_scores_bin(parsed):
    class_mat = get_product_file(parsed, 'class_scores')
    csv_out = '\n'.join(class_scoresmat2csv(class_mat, parsed['bin_lid']))
    return Response(csv_out + '\n', mimetype='text/csv')

def get_zip_entry_bytes(zipfile_path, entry_name):
    zipfile = ZipFile(zipfile_path)
    entry_bytes = zipfile.read(entry_name)
    zipfile.close()
    return entry_bytes

def serve_blob_image(parsed, mimetype, outline=False, target_img=None):
    # first, read the blob from the zipfile
    blob_zip = get_product_file(parsed, 'blobs')
    png_name = parsed['lid'] + '.png' # name is target LID + png extension
    png_data = get_zip_entry_bytes(blob_zip, png_name)
    # if we want a blob png, then pass it through without conversion
    if not outline and mimetype == 'image/png':
        return Response(png_data, mimetype='image/png')
    else:
        # read the png-formatted blob image into a PIL image
        pil_img = PIL.Image.open(StringIO(png_data))
        blob = np.array(pil_img.convert('L')) # convert to 8-bit grayscale
        if not outline: # unless we are drawing the outline
            return Response(as_bytes(blob), mimetype=mimetype) # format and serve
        else:
            blob_outline = find_boundaries(blob)
            roi = target_img
            blob = np.dstack([roi,roi,roi])
            blob[blob_outline] = [255,0,0]
            return Response(as_bytes(blob, mimetype), mimetype=mimetype)

############# ENDPOINTS ##################

# register security blueprint
# this may go away later, since flask-user takes care of
# most of our security requirements
SECURITY_URL_PREFIX = '/sec'
app.register_blueprint(security.security_blueprint,
    url_prefix=SECURITY_URL_PREFIX)

# register the admin blueprint right up front
# API_URL_PREFIX should move to a config area some time
API_URL_PREFIX = '/admin/api/v1'
app.register_blueprint(timeseries_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(instrument_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(manager_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(user_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(user_admin_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(role_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(password_blueprint, url_prefix=API_URL_PREFIX)
app.register_blueprint(keychain_blueprint, url_prefix=API_URL_PREFIX)

# serve admin interface
@app.route('/admin')
@roles_required('Admin')
def admin_root():
    print os.path.join(ADMIN_APP_DIR,'ifcbadmin.html')
    return send_from_directory(ADMIN_APP_DIR, 'ifcbadmin.html')

@app.route('/admin/<path:filename>')
@roles_required('Admin')
def serve_static_admin(filename):
    return send_from_directory(ADMIN_APP_DIR, filename)

# endpoint to determine if user is logged in as admin
@app.route('/is_admin')
@roles_required('Admin')
def is_admin():
    return Response(json.dumps(dict(logged_in=True)),mimetype=MIME_JSON)

@app.route('/api')
@app.route('/api.html')
def serve_doc():
    template = dict(static=STATIC)
    return template_response('api.html', **template)

@app.route('/about')
@app.route('/about.html')
def serve_about():
    template = dict(static=STATIC)
    return template_response('help.html', **template)

### timeseries endpoints ###

METRICS=['trigger_rate', 'temperature', 'humidity']

@app.route('/')
@app.route('/<ts_label>')
@app.route('/<ts_label>/')
@app.route('/<ts_label>/dashboard')
@app.route('/<ts_label>/dashboard/')
@app.route('/<ts_label>/dashboard/<url:pid>')
def serve_timeseries(ts_label=None, pid=None):
    template = {
        'static': STATIC,
        'time_series': ts_label,
        'all_metrics': METRICS
    }
    if pid is not None:
        template['pid'] = pid
    # fetch time series information
    all_series = []
    url_root = get_url_root()
    for ts in session.query(TimeSeries).filter(TimeSeries.enabled).order_by(TimeSeries.label):
        if ts_label is None: # no time series specified
            return redirect(os.path.join(url_root, ts.label), code=302)
        description = ts.description
        if not description:
            description = ts_label
        if ts.label == ts_label:
            template['page_title'] = html.fromstring(description).text_content()
            template['title'] = description
        all_series.append((ts.label, description))
    template['all_series'] = all_series
    template['base_url'] = url_root
    return template_response('timeseries.html', **template)

### feed / metrics API ###

## metrics ##

### data volume by day ###
@app.route('/<ts_label>/api/volume') # deprecated
@app.route('/<ts_label>/api/feed/volume')
@app.route('/<ts_label>/api/feed/volume/start/<datetime:start>/end/<datetime:end>')
def volume(ts_label,start=None,end=None):
    dv = []
    with Feed(session, ts_label) as feed:
        for row in feed.daily_data_volume(start,end):
            dv.append({
                'gb': float(row[0]),
                'bin_count': row[1],
                'day': str(row[2])
            })
    return Response(json.dumps(dv), mimetype=MIME_JSON)

def canonicalize_bin(ts_label, b):
    return {
        'pid': canonicalize(get_url_root(), ts_label, b.lid),
        'date': iso8601(b.sample_time.timetuple())
    }

@app.route('/<ts_label>/feed.json')
def serve_feed_json(ts_label):
    bins = []
    with Feed(session, ts_label) as feed:
        for b in feed.latest():
            bins.append(canonicalize_bin(ts_label, b))
    return Response(json.dumps(bins), mimetype=MIME_JSON)

# elapsed time since most recent bin before timestamp default now
@app.route('/<ts_label>/api/feed/elapsed')
@app.route('/<ts_label>/api/feed/elapsed/<datetime:timestamp>')
def elapsed(ts_label,timestamp=None):
    with Feed(session, ts_label) as feed:
        try:
            delta = feed.elapsed(timestamp=timestamp)
            return Response(json.dumps(dict(elapsed=delta.total_seconds())), mimetype=MIME_JSON)
        except IndexError:
            abort(404)

def ts_metric(ts_label, callback, start=None, end=None, s=None):
    if s is None:
        s = 86400
    if end is None:
        end = utcdtnow()
    if start is None:
        start = end - timedelta(seconds=s)
    with Feed(session, ts_label) as feed:
        result = []
        for b in feed.time_range(start, end):
            r = canonicalize_bin(ts_label, b)
            r.update(callback(b))
            result.append(r)
    return Response(json.dumps(result), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/feed/trigger_rate')
@app.route('/<ts_label>/api/feed/trigger_rate/last/<int:s>')
@app.route('/<ts_label>/api/feed/trigger_rate/end/<datetime:end>')
@app.route('/<ts_label>/api/feed/trigger_rate/end/<datetime:end>/last/<int:s>')
@app.route('/<ts_label>/api/feed/trigger_rate/start/<datetime:start>/end/<datetime:end>')
def trigger_rate(ts_label,start=None,end=None,s=None):
    def callback(b):
        return {
            'trigger_rate': float(b.trigger_rate)
        }
    return ts_metric(ts_label,callback,start,end,s)

@app.route('/<ts_label>/api/feed/temperature')
@app.route('/<ts_label>/api/feed/temperature/last/<int:s>')
@app.route('/<ts_label>/api/feed/temperature/end/<datetime:end>')
@app.route('/<ts_label>/api/feed/temperature/end/<datetime:end>/last/<int:s>')
@app.route('/<ts_label>/api/feed/temperature/start/<datetime:start>/end/<datetime:end>')
def temperature(ts_label,start=None,end=None,s=None):
    def callback(b):
        return {
            'temperature': float(b.temperature)
        }
    return ts_metric(ts_label,callback,start,end,s)

@app.route('/<ts_label>/api/feed/humidity')
@app.route('/<ts_label>/api/feed/humidity/last/<int:s>')
@app.route('/<ts_label>/api/feed/humidity/end/<datetime:end>')
@app.route('/<ts_label>/api/feed/humidity/end/<datetime:end>/last/<int:s>')
@app.route('/<ts_label>/api/feed/humidity/start/<datetime:start>/end/<datetime:end>')
def humidity(ts_label,start=None,end=None,s=None):
    def callback(b):
        return {
            'humidity': float(b.humidity)
        }
    return ts_metric(ts_label,callback,start,end,s)

## metric views ##

# FIXME configurable time range
def view_metrics(ts_label,metrics):
    with Feed(session, ts_label) as feed:
        # FIXME configurable time range
        for b in feed.latest():
            break
        then = iso8601(b.sample_time.timetuple())
        tmpl = {
            'static': STATIC,
            'timeseries': ts_label,
            'metrics': [{
                'endpoint': '/%s/api/feed/%s/end/%s' % (ts_label, metric, then),
                'metric': metric,
                'y_label': metric
            } for metric in metrics]
        }
        return template_response('instrument.html',**tmpl)

@app.route('/<ts_label>/trigger_rate.html')
def view_trigger_rate(ts_label):
    return view_metrics(ts_label,['trigger_rate'])

@app.route('/<ts_label>/temperature.html')
def view_temperature(ts_label):
    return view_metrics(ts_label,['temperature'])

@app.route('/<ts_label>/humidity.html')
def view_humidity(ts_label):
    return view_metrics(ts_label,['humidity'])

@app.route('/<ts_label>/metrics.html')
def view_all_metrics(ts_label):
    return view_metrics(ts_label,[
        'trigger_rate',
        'temperature',
        'humidity'])

### feed ####

@app.route('/<ts_label>/api/feed/nearest/<datetime:timestamp>')
def nearest(ts_label, timestamp):
    #ts = struct_time2utcdatetime(parse_date_param(timestamp))
    with Feed(session, ts_label) as feed:
        for bin in feed.nearest(timestamp=timestamp):
            break
    #sample_time_str = iso8601(bin.sample_time.timetuple())
    #pid = canonicalize(request.url_root, ts_label, bin.lid)
    resp = canonicalize_bin(ts_label, bin)
    return Response(json.dumps(resp), mimetype=MIME_JSON)

def feed_massage_bins(ts_label,bins):
    resp = []
    for bin in bins:
        sample_time_str = iso8601(bin.sample_time.timetuple())
        pid = canonicalize(get_url_root(), ts_label, bin.lid)
        resp.append(dict(pid=pid, date=sample_time_str))
    return resp

def _serve_feed_day(ts_label,dt,include_skip=False):
    with Feed(session, ts_label) as feed:
        bins = feed.day(dt,include_skip)
    resp = feed_massage_bins(ts_label, bins)
    return Response(json.dumps(resp), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/feed/day/<datetime:dt>')
def serve_feed_day(ts_label,dt):
    return _serve_feed_day(ts_label,dt)

@app.route('/<ts_label>/api/feed/day_skip/<datetime:dt>')
def serve_feed_day_skip(ts_label,dt):
    return _serve_feed_day(ts_label,dt,include_skip=True)

@app.route('/<ts_label>/api/feed/day_admin/<datetime:dt>')
def serve_day_admin(ts_label,dt):
    template = {
        'static': STATIC,
        'ts_label': ts_label,
        'date': iso8601(dt.date().timetuple()),
        'prev_date_href': '/%s/api/feed/day_admin/%s' % (ts_label, iso8601((dt.date() - timedelta(days=1)).timetuple())),
        'next_date_href': '/%s/api/feed/day_admin/%s' % (ts_label, iso8601((dt.date() + timedelta(days=1)).timetuple()))
    }
    return template_response('day_admin.html',**template)

@app.route('/<ts_label>/api/feed/<after_before>/pid/<url:pid>')
@app.route('/<ts_label>/api/feed/<after_before>/n/<int:n>/pid/<url:pid>')
def serve_after_before(ts_label,after_before,n=1,pid=None):
    if not after_before in ['before','after']:
        abort(400)
    try:
        parsed = next(ifcb().pid(pid))
    except StopIteration:
        abort(404)
    bin_lid = parsed['bin_lid']
    with Feed(session, ts_label) as feed:
        if after_before=='before':
            bins = list(feed.before(bin_lid, n))
        else:
            bins = list(feed.after(bin_lid, n))
    resp = feed_massage_bins(ts_label, bins)
    return Response(json.dumps(resp), mimetype=MIME_JSON)

def parsed2files(parsed):
    b = session.query(Bin).filter(and_(Bin.lid==parsed['lid'],Bin.ts_label==parsed['ts_label'])).first()
    if b is None:
        raise NotFound
    return b.files

def pid2files(ts_label,pid):
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        raise NotFound
    return parsed2files(parsed)

def file2dict(f):
    return {
        'filename': f.filename,
        'filetype': f.filetype,
        'length': f.length,
        'sha1': f.sha1,
        'fix_time': iso8601(f.fix_time.timetuple()),
        'local_path': f.local_path
    }

def get_files(parsed,check=False,fast=True):
    result = []
    for f in parsed2files(parsed):
        d = file2dict(f)
        if check:
            d['check'] = f.check_fixity(fast=fast)
        result.append(d)
    return result

@app.route('/<ts_label>/api/files/<url:pid>')
@roles_required('Admin')
def serve_files(ts_label, pid):
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        abort(404)
    try:
        result = get_files(parsed,check=True)
    except NotFound:
        abort(404)
    return Response(json.dumps(result), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/files/check/<url:pid>')
@roles_required('Admin')
def check_files(ts_label, pid):
    # FIXME handle ts_label + lid
    # FIXME fast
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        abort(404)
    result = get_files(parsed,check=True,fast=True) # FIXME set fast to false
    return Response(json.dumps(result), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/check_roots')
@roles_required('Admin')
def check_roots(ts_label):
    acc = Accession(session, ts_label)
    r = {}
    for root in acc.get_raw_roots():
        r[root] = False
        for fs in acc.list_filesets(root):
            r[root] = True
            break
    return Response(json.dumps(r), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/accede')
def accede(ts_label):
    # initiate batch accession
    key='ifcb:acc:%s' % ts_label
    workflow_client.wakeup(key)
    return Response(json.dumps(dict(wakeup_key=key)), mimetype=MIME_JSON)

### bins, targets, and products ###

def get_target_metadata(target,targets):
    """given target metadata, adjust its metadata"""
    try:
        del target[PAIR]
    except KeyError:
        pass # it's OK, this target isn't stitched
    ts = list(targets)
    for p,t,n in zip([None]+ts, ts, ts[1:]+[None]):
        if t[PID]==target[PID]:
            if p is not None: target['previous'] = p[PID]
            if n is not None: target['next'] = n[PID]
            break
    return target

def get_target_image(parsed, target, path=None, file=None, raw_stitch=False):
    if PAIR in target:
        (a,b) = target[PAIR]
        a_image = read_target_image(a, path=path, file=file)
        b_image = read_target_image(b, path=path, file=file)
        if raw_stitch:
            return stitch_raw((a,b),(a_image,b_image),background=180)
        else:
            try:
                bin_zip = get_product_file(parsed, BINZIP_PRODUCT)
                if os.path.exists(bin_zip):
                    # name is target LID + png extension
                    png_name = os.path.basename(target[PID]) + '.png'
                    png_data = get_zip_entry_bytes(bin_zip, png_name)
                    pil_img = PIL.Image.open(StringIO(png_data))
                    return np.array(pil_img.convert('L')) # convert to 8-bit grayscale
            except NotFound:
                pass
            im,_ = v1_stitching.stitch((a,b),(a_image,b_image))
            return im
    else:
        return read_target_image(target, path=path, file=file)

class DashboardRequest(object):
    def __init__(self, pid, request=None):
        try:
            self.parsed = parse_pid(pid)
        except StopIteration:
            abort(404)
        self.time_series = self.parsed['ts_label']
        self.bin_lid = self.parsed['bin_lid']
        self.lid = self.parsed[LID]
        self.schema_version = self.parsed[SCHEMA_VERSION]
        self.adc_cols = re.split(' ', self.parsed['adc_cols'])
        if request is not None:
            self.url_root = get_url_root()
        self.canonical_pid = canonicalize(self.url_root, self.time_series, self.lid)
        self.extension = 'json' # default
        if 'extension' in self.parsed:
            self.extension = self.parsed['extension']
        self.timestamp = get_timestamp(self.parsed)
        self.product = self.parsed[PRODUCT]

@app.route('/<url:pid>',methods=['GET'])
def serve_pid(pid):
    req = DashboardRequest(pid, request)
    try:
        paths = get_fileset(req.parsed)
    except NotFound:
        abort(404)
    hdr_path = paths['hdr_path']
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    adc = Adc(adc_path, req.schema_version)
    heft = 'full' # heft is either short, medium, or full
    if 'extension' in req.parsed:
        extension = req.parsed['extension']
    if 'target' in req.parsed:
        canonical_bin_pid = canonicalize(req.url_root, req.time_series, req.bin_lid)
        target_no = int(req.parsed['target'])
        # pull three targets, then find any stitched pair
        offset=target_no-1
        limit=3
        if target_no==1: # if target_no is 1, pull two targets
            offset=1
            limit=2
        targets = adc.get_some_targets(offset,limit)
        targets = list_stitched_targets(targets)
        for t in targets:
            if t[TARGET_NUMBER] == target_no:
                target = t
        add_pid(target, canonical_bin_pid)
        # check for image
        mimetype = mimetypes.types_map['.' + extension]
        if mimetype.startswith('image/'):
            if req.product=='raw':
                img = get_target_image(req.parsed, target, roi_path)
                return Response(as_bytes(img,mimetype),mimetype=mimetype)
            if req.product=='blob':
                return serve_blob_image(req.parsed, mimetype)
            if req.product=='blob_outline':
                img = get_target_image(req.parsed, target, roi_path)
                return serve_blob_image(req.parsed, mimetype, outline=True, target_img=img)
        # not an image, so get more metadata
        targets = get_targets(adc, canonical_bin_pid)
        # not an image, check for JSON
        if extension == 'json':
            return Response(json.dumps(target),mimetype=MIME_JSON)
        target = get_target_metadata(target,targets)
        # more metadata representations. we'll need the header
        hdr = parse_hdr_file(hdr_path)
        if extension == 'xml':
            return Response(target2xml(req.canonical_pid, target, req.timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension == 'rdf':
            return Response(target2rdf(req.canonical_pid, target, req.timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension in ['html', 'htm']:
            template = {
                'static': STATIC,
                'target_pid': req.canonical_pid,
                'bin_pid': canonical_bin_pid,
                'properties': target,
                'target': target.items(), # FIXME use order_keys
                'date': req.timestamp
            }
            return template_response('target.html',**template)
    else: # bin
        if req.extension in ['hdr', 'adc', 'roi']:
            path = dict(hdr=hdr_path, adc=adc_path, roi=roi_path)[req.extension]
            mimetype = dict(hdr='text/plain', adc='text/csv', roi='application/octet-stream')[req.extension]
            return Response(file(path,'rb'), direct_passthrough=True, mimetype=mimetype)
        try:
            if req.product in ['blobs','blob']: # accept old url pattern
                return serve_blob_bin(req.parsed)
            if req.product=='features':
                return serve_features_bin(req.parsed)
            if req.product=='class_scores':
                return serve_class_scores_bin(req.parsed)
        except NotFound:
            abort(404)
        # gonna need targets unless heft is medium or below
        targets = []
        if req.product != 'short':
            targets = get_targets(adc, req.canonical_pid)
        # end of views
        # not a special view, handle representations of targets
        if req.extension=='csv':
            adc_cols = req.parsed[ADC_COLS].split(' ')
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines)+'\n',mimetype='text/csv')
        # we'll need the header for the other representations
        hdr = parse_hdr_file(hdr_path)
        if req.extension in ['html', 'htm']:
            targets = list(targets)
            context, props = split_hdr(hdr)
            template = {
                'static': STATIC,
                'bin_pid': req.canonical_pid,
                'time_series': req.time_series,
                'context': context,
                'properties': props,
                'targets': targets,
                'target_pids': [t['pid'] for t in targets],
                'date': req.timestamp,
            }
            return template_response('bin.html', **template)
        if req.extension=='json':
            if req.product=='short':
                return Response(bin2json_short(req.canonical_pid,hdr,req.timestamp),mimetype=MIME_JSON)
            if req.product=='medium':
                return Response(bin2json_medium(req.canonical_pid,hdr,targets,req.timestamp),mimetype=MIME_JSON)
            return Response(bin2json(req.canonical_pid,hdr,targets,req.timestamp),mimetype=MIME_JSON)
        if req.extension=='xml':
            return Response(bin2xml(req.canonical_pid,hdr,targets,req.timestamp),mimetype='text/xml')
        if req.extension=='rdf':
            return Response(bin2rdf(req.canonical_pid,hdr,targets,req.timestamp),mimetype='text/xml')
        if req.extension=='zip':
            # look to see if the zipfile is resolvable
            try:
                zip_path = get_product_file(req.parsed, 'binzip')
                if os.path.exists(zip_path):
                    return Response(file(zip_path), direct_passthrough=True, mimetype='application/zip')
            except NotFound:
                pass
            except:
                raise
            buffer = BytesIO()
            bin2zip(req.parsed,req.canonical_pid,targets,hdr,req.timestamp,roi_path,buffer)
            return Response(buffer.getvalue(), mimetype='application/zip')
    return 'unimplemented'

####### deposit ########

@app.route('/<url:pid>',methods=['PUT'])
def deposit(pid):
    req = DashboardRequest(pid, request)
    try:
        destpath = files.get_product_destination(session, pid)
    except NotFound:
        abort(404)
    product_data = request.data
    destpath_part = '%s_%s.part' % (destpath, gen_id())
    try:
        os.makedirs(os.path.dirname(destpath))
    except:
        pass
    with open(destpath_part,'w') as out:
        shutil.copyfileobj(StringIO(product_data), out)
    os.rename(destpath_part, destpath)
    utcnow = iso8601()
    message = '%s wrote %d bytes to %s' % (utcnow, len(product_data), destpath)
    return Response(json.dumps(dict(
        status='OK',
        time=utcnow,
        message=message,
        pid=pid,
        path=destpath
    )), mimetype=MIME_JSON)

#### scatterplots ####

def scatter_json(targets,bin_pid,x_axis,y_axis,features={}):
    # FIXME need a way to map between generic cols and schema-dependent cols
    points = []
    for t in targets:
        roi_num = re.sub(r'.*_','',t[PID])# strip prefix
        # This isn't very elegant, if they enter an invalid
        # column it will error, but it was like that before too
        if x_axis in t:
            x = t[x_axis]
        else:
            x = features[int(roi_num)][x_axis]
        if y_axis in t:
            y = t[y_axis]
        else:
            y = features[int(roi_num)][y_axis]

        point = {
            'roi_num': roi_num,
            'x': x,
            'y': y
        }
        points.append(point)
        
    d = {
        'bin_pid': bin_pid,
        'x_axis_label': x_axis,
        'y_axis_label': y_axis,
        'points': points
    }
    return Response(json.dumps(d), mimetype=MIME_JSON)

@memoize(key=lambda args: args[0].time_series)
def get_features_schema(req, features_path=None):
    if features_path is None:
        # will raise NotFound if not features file is found,
        # caller must catch to provide default value in this case
        features_path = get_product_file(req.parsed,'features')
    features_source = LocalFileSource(features_path)
    for row in read_csv(features_source, None, 0, 1):
        return row

@app.route('/<time_series>/api/plot/schema/pid/<url:pid>')
def plot_schema(time_series, pid):
    req = DashboardRequest(pid, request)
    skip_adc_cols = ['binID', 'pid', 'trigger', 'byteOffset']
    adc_cols = [c for c in req.adc_cols if c not in skip_adc_cols]
    try:
        feature_schema = get_features_schema(req)
    except NotFound:
        feature_schema = {}
    feature_cols = [feature_schema[k] for k in sorted(feature_schema)]
    def is_tail_col(c):
        return re.match(r'^(Wedge|Ring|HOG)',c) is not None
    fc_head = [c for c in feature_cols if not is_tail_col(c)]
    fc_tail = [c for c in feature_cols if is_tail_col(c)]
    return Response(json.dumps(adc_cols + fc_head + fc_tail), mimetype=MIME_JSON)

def read_features(features_path):
    features_source = LocalFileSource(features_path)
    for row in read_csv(features_source, None, 1, NO_LIMIT):
        yield row

@app.route('/<time_series>/api/plot/<path:params>/pid/<url:pid>')
@app.route('/<time_series>/api/plot/<path:params>/pid/<url:pid>')
def scatter(time_series,params,pid):
    req = DashboardRequest(pid, request)
    params = parse_params(params, x='bottom', y='left')
    try:
        paths = get_fileset(req.parsed)
    except NotFound:
        abort(404)
    adc_path = paths['adc_path']
    adc = Adc(adc_path, req.schema_version)
    targets = get_targets(adc, req.canonical_pid)
    
    # check if we need to use features file
    features_targets = {}
    if params['x'] not in req.adc_cols or params['y'] not in req.adc_cols:
        try:
            features_path = get_product_file(req.parsed,'features')
        except NotFound:
            abort(404)
        columns = get_features_schema(req, features_path)
        for target in read_features(features_path):
            new_target = {}
            for i,v in columns.items():
                new_target[v] = target[i]
            # dict indexed by roi_number
            features_targets[int(new_target['roi_number'])] = new_target
        
    # handle some target views other than the standard ones
    if req.extension=='json':
        return scatter_json(targets,req.canonical_pid,params['x'],params['y'],features_targets)
    abort(404)

#### workflow ####

@app.route('/api/workflow/recent')
@app.route('/api/workflow/recent/<int:n>')
def serve_wf_recent(n=None):
    r = workflow_client.most_recent(n)
    return Response(json.dumps(r), mimetype=MIME_JSON)

#### skipping and tagging ####

def get_orm_bin(req):
    b = session.query(Bin).filter(and_(Bin.lid==req.lid,Bin.ts_label==req.time_series)).first()
    if b is None:
        abort(404)
    return b

@app.route('/api/get_skip/<url:pid>')
def get_skip_flag(pid):
    req = DashboardRequest(pid, request)
    b = get_orm_bin(req)
    result = {
        'operation': 'get skip flag',
        'skip': b.skip,
        'pid': pid
    }
    return Response(json.dumps(result),mimetype=MIME_JSON)

def get_orm_bin(req):
    b = session.query(Bin).filter(and_(Bin.lid==req.lid,Bin.ts_label==req.time_series)).first()
    if b is None:
        abort(404)
    return b

def set_skip_flag(b,value):
    b.skip = value
    session.commit()
    result = {
        'operation': 'set skip flag',
        'skip': b.skip,
        'lid': b.lid
    }
    return result

@app.route('/api/skip/<url:pid>')
@roles_required('Admin')
def skip_bin(pid):
    req = DashboardRequest(pid, request)
    b = get_orm_bin(req)
    r = set_skip_flag(b,True)
    return Response(json.dumps(r),mimetype=MIME_JSON)

@app.route('/api/unskip/<url:pid>')
@roles_required('Admin')
def unskip_bin(pid):
    req = DashboardRequest(pid, request)
    b = get_orm_bin(req)
    r = set_skip_flag(b,False)
    return Response(json.dumps(r),mimetype=MIME_JSON)

def _skip_or_unskip_day(ts_label, dt, skip=True):
    with Feed(session, ts_label) as feed:
        bins = feed.day(dt,include_skip=True)
    for b in bins:
        b.skip = skip
    session.commit()
    r = {
        'day': iso8601(dt.timetuple())
    }
    return Response(json.dumps(r), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/skip_day/<datetime:dt>')
@roles_required('Admin')
def skip_day(ts_label,dt):
    return _skip_or_unskip_day(ts_label, dt, skip=True)

@app.route('/<ts_label>/api/unskip_day/<datetime:dt>')
@roles_required('Admin')
def unskip_day(ts_label,dt):
    return _skip_or_unskip_day(ts_label, dt, skip=False)

#### mosaics #####

def get_sorted_tiles(adc_path, schema_version, bin_pid):
    # read ADC and convert to Tiles in size-descending order
    def descending_size(t):
        (w,h) = t.size
        return 0 - (w * h)
    adc = Adc(adc_path, schema_version)
    tiles = [Tile(t, (t[HEIGHT], t[WIDTH])) for t in get_targets(adc, bin_pid)]
    # FIXME instead of sorting tiles, sort targets to allow for non-geometric sort options
    tiles.sort(key=descending_size)
    return tiles

def get_mosaic_layout(adc_path, schema_version, bin_pid, scaled_size, page):
    tiles = get_sorted_tiles(adc_path, schema_version, bin_pid)
    # perform layout operation
    return list(mosaic.layout(tiles, scaled_size, page, threshold=0.05))

def layout2json(layout, scale):
    """Doesn't actually produce JSON but rather JSON-serializable representation of the tiles"""
    for t in layout:
        (w,h) = t.size
        (x,y) = t.position
        yield dict(pid=t.image['pid'], width=int(w*scale), height=int(h*scale), x=int(x*scale), y=int(y*scale))

def parse_mosaic_params(params):
    SIZE, SCALE, PAGE = 'size', 'scale', 'page'
    params = parse_params(params, size='1024x1024',page=1,scale=1.0)
    size = tuple(map(int,re.split('x',params[SIZE])))
    scale = float(params[SCALE])
    page = int(params[PAGE])
    return (size, scale, page)

@app.route('/<time_series>/api/mosaic/<path:params>/pid/<url:pid>')
def serve_mosaic_image(time_series=None, pid=None, params='/'):
    """Generate a mosaic of ROIs from a sample bin.
    params include the following, with default values
    - series (mvco) - time series (FIXME: handle with resolver, clarify difference between namespace, time series, pid, lid)
    - size (1024x1024) - size of the mosaic image
    - page (1) - page. for typical image sizes the entire bin does not fit and so is split into pages.
    - scale - scaling factor for image dimensions """
    # parse params
    size, scale, page = parse_mosaic_params(params)
    (w,h) = size
    parsed = parse_pid(pid)
    schema_version = parsed['schema_version']
    try:
        paths = get_fileset(parsed)
    except NotFound:
        abort(404)
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    bin_pid = canonicalize(get_url_root(), time_series, parsed['bin_lid'])
    # perform layout operation
    scaled_size = (int(w/scale), int(h/scale))
    layout = list(get_mosaic_layout(adc_path, schema_version, bin_pid, scaled_size, page))
    extension = parsed['extension']
    # serve JSON on request
    if extension == 'json':
        return Response(json.dumps(list(layout2json(layout, scale))), mimetype=MIME_JSON)
    mimetype = mimetypes.types_map['.' + extension]
    # read all images needed for compositing and inject into Tiles
    image_layout = []
    with open(roi_path,'rb') as roi_file:
        for tile in layout:
            target = tile.image # in mosaic API, the record is called 'image'
            # FIXME 1. replace PIL
            image = get_target_image(parsed, target, file=roi_file, raw_stitch=True)
            image_layout.append(Tile(PIL.Image.fromarray(image), tile.size, tile.position))
    # produce and serve composite image
    mosaic_image = thumbnail(mosaic.composite(image_layout, scaled_size, mode='L', bgcolor=160), (w,h))
    #pil_format = filename2format('foo.%s' % extension)
    return Response(as_bytes(mosaic_image), mimetype=mimetype)

if __name__ == '__main__':
    from oii.ifcb2.session import dbengine
    init_database(dbengine,session)
    # finally, start the application
    app.run(host='0.0.0.0',port=8080)
