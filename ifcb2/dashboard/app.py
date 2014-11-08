import os
import mimetypes
import json
from time import strptime
from io import BytesIO
import re
import PIL
from array import array
from zipfile import ZipFile
from lxml import html
from StringIO import StringIO
from datetime import timedelta

from flask import Flask, Response, abort, request, render_template, render_template_string, redirect
import flask.ext.sqlalchemy
import flask.ext.restless
from flask.ext.user import UserManager, SQLAlchemyAdapter

from sqlalchemy import and_

import numpy as np

from skimage.segmentation import find_boundaries

from oii.utils import coalesce, memoize
from oii.times import iso8601, parse_date_param, struct_time2utcdatetime, utcdtnow
from oii.image.io import as_bytes, as_pil
from oii.image import mosaic
from oii.image.mosaic import Tile
from oii.webapi.utils import UrlConverter, DatetimeConverter

# FIXME this is used for old PIL-based mosaic compositing API
from oii.image.pil.utils import filename2format, thumbnail

from oii.ifcb2 import get_resolver
from oii.ifcb2.orm import Base, Bin, TimeSeries, DataDirectory, User
from oii.ifcb2.session import session, dbengine

from oii.ifcb2.dashboard.admin_api import timeseries_blueprint, manager_blueprint
from oii.ifcb2.dashboard.admin_api import user_blueprint, password_blueprint, instrument_blueprint
from oii.ifcb2.dashboard import security

from oii.ifcb2.feed import Feed
from oii.ifcb2.formats.adc import Adc

from oii.ifcb2.files import parsed_pid2fileset, NotFound
from oii.ifcb2.identifiers import add_pids, add_pid, canonicalize
from oii.ifcb2.represent import split_hdr, targets2csv, bin2xml, bin2json, bin2rdf, bin2zip, target2xml, target2rdf, bin2json_short, bin2json_medium
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.hdr import parse_hdr_file
from oii.ifcb2.accession import fast_accession
# keys
from oii.ifcb2.identifiers import PID, LID, ADC_COLS, SCHEMA_VERSION, TIMESTAMP, TIMESTAMP_FORMAT, PRODUCT
from oii.ifcb2.formats.adc import HEIGHT, WIDTH, TARGET_NUMBER
from oii.ifcb2.stitching import STITCHED, PAIR, list_stitched_targets, stitch_raw

# constants

MIME_JSON='application/json'

STATIC='/static/'
app = Flask(__name__)
app.url_map.converters['url'] = UrlConverter
app.url_map.converters['datetime'] = DatetimeConverter

# load Flask-User configuration and init
# this gets us authn/authz and session management
app.config.from_object('oii.ifcb2.dashboard.security_config')
db_adapter = SQLAlchemyAdapter(dbengine, User)
user_manager = UserManager(db_adapter, app)

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
app.register_blueprint(password_blueprint, url_prefix=API_URL_PREFIX)

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
    dds = session.query(DataDirectory)\
                .join(TimeSeries)\
                .filter(TimeSeries.label==ts_label)\
                .filter(DataDirectory.product_type==product_type)
    paths = []
    for data_dir in dds:
        paths.append(data_dir.path)
    return paths

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

def serve_blob_image(parsed, mimetype, outline=False, target_img=None):
    # first, read the blob from the zipfile
    blob_zip = get_product_file(parsed, 'blobs')
    zipfile = ZipFile(blob_zip)
    png_name = parsed['lid'] + '.png' # name is target LID + png extension
    png_data = zipfile.read(png_name)
    zipfile.close()
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
@app.route('/<ts_label>/dashboard/<path:pid>')
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
    for ts in session.query(TimeSeries).filter(TimeSeries.enabled):
        if ts_label is None: # no time series specified
            return redirect(os.path.join(request.url_root, ts.label), code=302)
        if ts.label == ts_label:
            template['page_title'] = html.fromstring(ts.description).text_content()
            template['title'] = ts.description
        all_series.append((ts.label, ts.description))
    template['all_series'] = all_series
    template['base_url'] = request.url_root
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
                'day': row[2]
            })
    return Response(json.dumps(dv), mimetype=MIME_JSON)

def canonicalize_bin(ts_label, b):
    return {
        'pid': canonicalize(request.url_root, ts_label, b.lid),
        'date': iso8601(b.sample_time.timetuple())
    }

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
def view_metric(ts_label,metric):
    with Feed(session, ts_label) as feed:
        # FIXME configurable time range
        for b in feed.latest():
            break
        then = iso8601(b.sample_time.timetuple())
        tmpl = {
            'static': STATIC,
            'endpoint': '/%s/api/feed/%s/end/%s' % (ts_label, metric, then),
            'metric': metric,
            'y_label': metric
        }
        return template_response('step_graph.html',**tmpl)

@app.route('/<ts_label>/trigger_rate.html')
def view_trigger_rate(ts_label):
    return view_metric(ts_label,'trigger_rate')

@app.route('/<ts_label>/temperature.html')
def view_temperature(ts_label):
    return view_metric(ts_label,'temperature')

@app.route('/<ts_label>/humidity.html')
def view_humidity(ts_label):
    return view_metric(ts_label,'humidity')

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

@app.route('/<ts_label>/api/feed/<after_before>/pid/<path:pid>')
@app.route('/<ts_label>/api/feed/<after_before>/n/<int:n>/pid/<path:pid>')
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
    resp = []
    for bin in bins:
        sample_time_str = iso8601(bin.sample_time.timetuple())
        pid = canonicalize(request.url_root, ts_label, bin.lid)
        resp.append(dict(pid=pid, date=sample_time_str))
    return Response(json.dumps(resp), mimetype=MIME_JSON)

def parsed2files(parsed):
    b = session.query(Bin).filter(and_(Bin.lid==parsed['lid'],Bin.ts_label==parsed['ts_label'])).first()
    if b is None:
        abort(404)
    return b.files

def pid2files(ts_label,pid):
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        abort(404)
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

def get_files(parsed,check=False):
    result = []
    for f in parsed2files(parsed):
        d = file2dict(f)
        if check:
            d['check'] = f.check_fixity(fast=True)
        result.append(d)
    return result

@app.route('/<ts_label>/api/files/<path:pid>')
def serve_files(ts_label, pid):
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        abort(404)
    result = get_files(parsed)
    return Response(json.dumps(result), mimetype=MIME_JSON)

@app.route('/<ts_label>/api/files/check/<path:pid>')
def check_files(ts_label, pid):
    # FIXME handle ts_label + lid
    # FIXME fast
    parsed = { 'ts_label': ts_label }
    try:
        parsed.update(parse_pid(pid))
    except StopIteration:
        abort(404)
    result = get_files(parsed,check=True)
    return Response(json.dumps(result), mimetype=MIME_JSON)

### data validation and accession ###

@app.route('/api/accession')
@app.route('/<ts_label>/api/accession')
def accession(ts_label=None):
    results = []
    tss = []
    if ts_label is None:
        for ts in session.query(TimeSeries).filter(TimeSeries.enabled):
            results.append(ts)
    else:
        tss = [session.query(TimeSeries).filter(TimeSeries.label==ts_label).first()]
    for ts in tss:
        for ddir in ts.data_dirs:
            if ddir.product_type != 'raw':
                continue
            try:
                (n_new, n_total) = fast_accession(session, ts.label, ddir.path)
                results.append({
                    'time_series': ts.label,
                    'data_dir': ddir.path,
                    'status': 'found',
                    'new': n_new,
                    'total': n_total
                })
            except:
                raise # FIXME
                results.append({
                    'time_series': ts.label,
                    'data_dir': ddir.path,
                    'status': 'not found'
                });
    return Response(json.dumps(results), mimetype='application/json')

### bins, targets, and products ###

def get_target_metadata(target):
    """given target metadata, clean it up"""
    try:
        del target[PAIR]
    except KeyError:
        pass # it's OK, this target isn't stitched
    return target

def get_target_image(target, path=None, file=None, raw_stitch=True):
    if PAIR in target:
        (a,b) = target[PAIR]
        a_image = read_target_image(a, path=path, file=file)
        b_image = read_target_image(b, path=path, file=file)
        if raw_stitch:
            return stitch_raw((a,b),(a_image,b_image))
        else:
            return stitch_raw((a,b),(a_image,b_image)) # FIXME full stitch
    else:
        return read_target_image(target, path=path, file=file)

def scatter_csv(targets,x_axis,y_axis):
    def t2c():
        yield 'pid,%s,%s' % (x_axis, y_axis)
        for t in targets:
            yield '%s,%s,%s' % (t['pid'], t[x_axis], t[y_axis])
    return Response('\n'.join(list(t2c()))+'\n',mimetype='text/csv')

def scatter_view(pid,view,x_axis,y_axis):
    tmpl = {
        'pid': pid,
        'endpoint': '%s_%s.csv' % (pid, view),
        'x_axis': x_axis,
        'x_axis_label': x_axis,
        'y_axis': y_axis,
        'y_axis_label': y_axis,
        'static': STATIC
    }
    return template_response('scatter.html',**tmpl)

@app.route('/<path:pid>')
def hello_world(pid):
    try:
        parsed = parse_pid(pid)
    except StopIteration:
        abort(404)
    time_series = parsed['ts_label']
    bin_lid = parsed['bin_lid']
    lid = parsed[LID]
    url_root = request.url_root
    canonical_pid = canonicalize(url_root, time_series, lid)
    schema_version = parsed[SCHEMA_VERSION]
    try:
        paths = get_fileset(parsed)
    except NotFound:
        abort(404)
    hdr_path = paths['hdr_path']
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    adc = Adc(adc_path, schema_version)
    extension = 'json' # default
    product = parsed[PRODUCT]
    heft = 'full' # heft is either short, medium, or full
    if 'extension' in parsed:
        extension = parsed['extension']
    timestamp = get_timestamp(parsed)
    if 'target' in parsed:
        canonical_bin_pid = canonicalize(url_root, time_series, bin_lid)
        target_no = int(parsed['target'])
        # pull three targets, then find any stitched pair
        targets = adc.get_some_targets(target_no-1, 3)
        targets = list_stitched_targets(targets)
        for t in targets:
            if t[TARGET_NUMBER] == target_no:
                target = t
        add_pid(target, canonical_bin_pid)
        if extension == 'json':
            return Response(json.dumps(target),mimetype=MIME_JSON)
        # not JSON, check for image
        mimetype = mimetypes.types_map['.' + extension]
        if mimetype.startswith('image/'):
            if product=='raw':
                img = get_target_image(target, roi_path)
                return Response(as_bytes(img,mimetype),mimetype=mimetype)
            if product=='blob':
                return serve_blob_image(parsed, mimetype)
            if product=='blob_outline':
                img = get_target_image(target, roi_path)
                return serve_blob_image(parsed, mimetype, outline=True, target_img=img)
        # not an image, so remove stitching information from metadata
        target = get_target_metadata(target)
        # more metadata representations. we'll need the header
        hdr = parse_hdr_file(hdr_path)
        if extension == 'xml':
            return Response(target2xml(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension == 'rdf':
            return Response(target2rdf(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension in ['html', 'htm']:
            template = {
                'static': STATIC,
                'target_pid': canonical_pid,
                'bin_pid': canonical_bin_pid,
                'properties': target,
                'target': target.items(), # FIXME use order_keys
                'date': timestamp
            }
            return template_response('target.html',**template)
    else: # bin
        if extension in ['hdr', 'adc', 'roi']:
            path = dict(hdr=hdr_path, adc=adc_path, roi=roi_path)[extension]
            mimetype = dict(hdr='text/plain', adc='text/csv', roi='application/octet-stream')[extension]
            return Response(file(path), direct_passthrough=True, mimetype=mimetype)
        if product=='blob':
            return serve_blob_bin(parsed)
        if product=='features':
            return serve_features_bin(parsed)
        # gonna need targets unless heft is medium or below
        targets = []
        if product != 'short':
            targets = get_targets(adc, canonical_pid)
        # handle some target views other than the standard ones
        if product=='xy': # a view, more than a product
            if extension=='csv':
                return scatter_csv(targets,'left','bottom')
            else:
                return scatter_view(canonical_pid,'xy','left','bottom')
        if product=='fs': # another scatter view
            # f/s for schema version v1 is fluorescenceLow / scatteringLow
            if schema_version=='v1':
                f_axis, s_axis = 'fluorescenceLow', 'scatteringLow'
            else:
                f_axis, s_axis = 'pmtA', 'pmtB'
            if extension=='csv':
                return scatter_csv(targets,f_axis,s_axis)
            else:
                return scatter_view(canonical_pid,'fs',f_axis,s_axis)
        # end of views
        # not a special view, handle representations of targets
        if extension=='csv':
            adc_cols = parsed[ADC_COLS].split(' ')
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines)+'\n',mimetype='text/csv')
        # we'll need the header for the other representations
        hdr = parse_hdr_file(hdr_path)
        # and the timestamp
        timestamp = iso8601(strptime(parsed['timestamp'], parsed['timestamp_format']))
        if extension in ['html', 'htm']:
            targets = list(targets)
            context, props = split_hdr(hdr)
            template = {
                'static': STATIC,
                'bin_pid': canonical_pid,
                'time_series': time_series,
                'context': context,
                'properties': props,
                'targets': targets,
                'target_pids': [t['pid'] for t in targets],
                'date': timestamp,
                'files': get_files(parsed,check=True) # note: ORM call!
            }
            print get_files(parsed)
            return template_response('bin.html', **template)
        if extension=='json':
            if product=='short':
                return Response(bin2json_short(canonical_pid,hdr,timestamp),mimetype=MIME_JSON)
            if product=='medium':
                return Response(bin2json_medium(canonical_pid,hdr,targets,timestamp),mimetype=MIME_JSON)
            return Response(bin2json(canonical_pid,hdr,targets,timestamp),mimetype=MIME_JSON)
        if extension=='xml':
            return Response(bin2xml(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='rdf':
            return Response(bin2rdf(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='zip':
            buffer = BytesIO()
            bin2zip(parsed,canonical_pid,targets,hdr,timestamp,roi_path,buffer)
            return Response(buffer.getvalue(), mimetype='application/zip')
    return 'unimplemented'

#### mosaics #####

@memoize
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

@memoize
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

@app.route('/<time_series>/api/mosaic/<path:params>/pid/<path:pid>')
def serve_mosaic_image(time_series=None, pid=None, params='/'):
    """Generate a mosaic of ROIs from a sample bin.
    params include the following, with default values
    - series (mvco) - time series (FIXME: handle with resolver, clarify difference between namespace, time series, pid, lid)
    - size (1024x1024) - size of the mosaic image
    - page (1) - page. for typical image sizes the entire bin does not fit and so is split into pages.
    - scale - scaling factor for image dimensions """
    # parse params
    SIZE, SCALE, PAGE = 'size', 'scale', 'page'
    params = parse_params(params, size='1024x1024',page=1,scale=1.0)
    (w,h) = tuple(map(int,re.split('x',params[SIZE])))
    scale = float(params[SCALE])
    page = int(params[PAGE])
    # parse pid/lid
    parsed = parse_pid(pid)
    schema_version = parsed['schema_version']
    try:
        paths = get_fileset(parsed)
    except NotFound:
        abort(404)
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    bin_pid = canonicalize(request.url_root, time_series, parsed['bin_lid'])
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
            image = get_target_image(target, file=roi_file, raw_stitch=True)
            image_layout.append(Tile(PIL.Image.fromarray(image), tile.size, tile.position))
    # produce and serve composite image
    mosaic_image = thumbnail(mosaic.composite(image_layout, scaled_size, mode='L', bgcolor=160), (w,h))
    #pil_format = filename2format('foo.%s' % extension)
    return Response(as_bytes(mosaic_image), mimetype=mimetype)

if __name__ == '__main__':
    from oii.ifcb2.session import dbengine
    Base.metadata.create_all(dbengine)
    app.run(host='0.0.0.0',port=8080,debug=True)
