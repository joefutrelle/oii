from flask import Flask, Response, abort, request, render_template, render_template_string

import mimetypes
import json
from time import strptime
from io import BytesIO

from oii.utils import coalesce, memoize
from oii.times import iso8601, parse_date_param, struct_time2utcdatetime
from oii.image.io import as_bytes

from oii.ifcb2 import get_resolver
from oii.ifcb2.feed import Feed
from oii.ifcb2.files import parsed_pid2fileset, NotFound
from oii.ifcb2.identifiers import add_pids, add_pid, canonicalize
from oii.ifcb2.represent import targets2csv, bin2xml, bin2json, bin2rdf, bin2zip, target2xml, target2rdf, bin2json_short, bin2json_medium
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.adc import Adc
from oii.ifcb2.formats.hdr import parse_hdr_file
from oii.ifcb2.orm import Bin, TimeSeries, DataDirectory

# keys
from oii.ifcb2.identifiers import PID, LID, ADC_COLS, SCHEMA_VERSION, TIMESTAMP, TIMESTAMP_FORMAT, PRODUCT
from oii.ifcb2.stitching import STITCHED

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# eventually the session cofiguration should
# go in its own class.
#SQLITE_URL='sqlite:///home/ubuntu/dev/ifcb_admin.db'
SQLITE_URL='sqlite:///ifcb_admin.db'

from sqlalchemy.pool import StaticPool
dbengine = create_engine(SQLITE_URL,
                    connect_args={'check_same_thread':False},
                    poolclass=StaticPool,
                    echo=True)
Session = sessionmaker(bind=dbengine)
session = Session()

STATIC='/static/'
app = Flask(__name__)

def ifcb():
    return get_resolver().ifcb

@memoize(ttl=30)
def get_data_roots(ts_label):
    ts = session.query(TimeSeries)\
                .filter(TimeSeries.label==ts_label)\
                .first()
    if ts is None:
        raise NotFound('Unknown time series %s' % ts_label)
    paths = []
    for data_dir in ts.data_dirs:
        paths.append(data_dir.path)
        return paths

def get_timestamp(parsed_pid):
    return iso8601(strptime(parsed_pid[TIMESTAMP], parsed_pid[TIMESTAMP_FORMAT]))

def get_targets(adc, bin_pid):
    # unstitched for now
    us_targets = add_pids(adc.get_targets(),bin_pid)
    for us_target in us_targets:
        # claim all are unstitched
        us_target[STITCHED] = False
        yield us_target

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

@app.route('/<ts_label>')
@app.route('/<ts_label>/')
@app.route('/<ts_label>/dashboard')
@app.route('/<ts_label>/dashboard/')
@app.route('/<ts_label>/dashboard/<path:pid>')
def serve_timeseries(ts_label='mvco', pid=None):
    template = dict(static=STATIC, time_series=ts_label)
    if pid is not None:
        template['pid'] = pid
    template['base_url'] = 'http://foo.bar/' # FIXME mock
    template['page_title'] = '{page title}' # FIXME mock
    template['title'] = '{title}' # FIXME mock
    template['all_series'] = [('label','name')] # FIXME mock
    return template_response('timeseries.html', **template)

@app.route('/<ts_label>/api/volume')
def volume(ts_label):
    dv = []
    with Feed(session, ts_label) as feed:
        for row in feed.daily_data_volume():
            dv.append({
                'gb': float(row[0]),
                'bin_count': row[1],
                'day': row[2]
            })
    return Response(json.dumps(dv), mimetype='application/json')

@app.route('/<ts_label>/api/feed/nearest/<timestamp>')
def nearest(ts_label, timestamp):
    ts = struct_time2utcdatetime(parse_date_param(timestamp))
    with Feed(session, ts_label) as feed:
        for bin in feed.nearest(timestamp=ts):
            break
    sample_time_str = iso8601(bin.sample_time.timetuple())
    pid = canonicalize(request.url_root, ts_label, bin.lid)
    resp = dict(pid=pid, date=sample_time_str)
    return Response(json.dumps(resp), mimetype='application/json')

@app.route('/<path:pid>')
def hello_world(pid):
    try:
        parsed = next(ifcb().pid(pid))
    except StopIteration:
        abort(404)
    time_series = parsed['ts_label']
    bin_lid = parsed['bin_lid']
    lid = parsed[LID]
    url_root = request.url_root
    canonical_pid = canonicalize(url_root, time_series, lid)
    try:
        data_roots = list(get_data_roots(time_series))
    except NotFound:
        abort(404)
    schema_version = parsed[SCHEMA_VERSION]
    adc_cols = parsed[ADC_COLS].split(' ')
    try:
        paths = parsed_pid2fileset(parsed,data_roots)
    except NotFound:
        abort(404)
    except:
        abort(500)
    hdr_path = paths['hdr_path']
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    adc = Adc(adc_path, schema_version)
    extension = 'json' # default
    product = parsed[PRODUCT] # should default to raw
    heft = 'full' # heft is either short, medium, or full
    if 'extension' in parsed:
        extension = parsed['extension']
    timestamp = get_timestamp(parsed)
    if 'target' in parsed:
        canonical_bin_pid = canonicalize(url_root, time_series, bin_lid)
        target_no = parsed['target']
        target = adc.get_target(target_no)
        add_pid(target, canonical_bin_pid)
        if extension == 'json':
            return Response(json.dumps(target),mimetype='application/json')
        # not JSON, check for image
        mimetype = mimetypes.types_map['.' + extension]
        if mimetype.startswith('image/'):
            img = read_target_image(target, roi_path)
            return Response(as_bytes(img,mimetype),mimetype=mimetype)
        # more metadata representations. we'll need the header
        hdr = parse_hdr_file(hdr_path)
        if extension == 'xml':
            return Response(target2xml(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
        if extension == 'rdf':
            return Response(target2rdf(canonical_pid, target, timestamp, canonical_bin_pid), mimetype='text/xml')
    else: # bin
        if extension in ['hdr', 'adc', 'roi']:
            path = dict(hdr=hdr_path, adc=adc_path, roi=roi_path)[extension]
            mimetype = dict(hdr='text/plain', adc='text/csv', roi='application/octet-stream')[extension]
            return Response(file(path), direct_passthrough=True, mimetype=mimetype)
        # gonna need targets unless heft is medium or below
        targets = []
        if product != 'short':
            targets = get_targets(adc, canonical_pid)
        if extension=='csv':
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines)+'\n',mimetype='text/csv')
        # we'll need the header for the other representations
        hdr = parse_hdr_file(hdr_path)
        # and the timestamp
        timestamp = iso8601(strptime(parsed['timestamp'], parsed['timestamp_format']))
        if extension=='json':
            if product=='short':
                return Response(bin2json_short(canonical_pid,hdr,timestamp),mimetype='application/json')
            if product=='medium':
                return Response(bin2json_medium(canonical_pid,hdr,targets,timestamp),mimetype='application/json')
            return Response(bin2json(canonical_pid,hdr,targets,timestamp),mimetype='application/json')
        if extension=='xml':
            return Response(bin2xml(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='rdf':
            return Response(bin2rdf(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='zip':
            buffer = BytesIO()
            bin2zip(parsed,canonical_pid,targets,hdr,timestamp,roi_path,buffer)
            return Response(buffer.getvalue(), mimetype='application/zip')
    return 'unimplemented'

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=True)
