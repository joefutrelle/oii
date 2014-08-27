from flask import Flask, Response, abort, request

import mimetypes
import json
from time import strptime

from oii.utils import coalesce, memoize
from oii.times import iso8601
from oii.image.io import as_bytes

from oii.ifcb2 import get_resolver
from oii.ifcb2.files import parsed_pid2fileset, NotFound
from oii.ifcb2.identifiers import add_pids, add_pid, canonicalize
from oii.ifcb2.represent import targets2csv, bin2xml, bin2json, bin2rdf
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.adc import Adc
from oii.ifcb2.formats.hdr import parse_hdr_file
from oii.ifcb2.orm import Bin, TimeSeries, DataDirectory

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

def get_targets(adc, bin_pid):
    # unstitched for now
    us_targets = add_pids(adc.get_targets(),bin_pid)
    for us_target in us_targets:
        # claim all are unstitched
        us_target['stitched'] = False
        yield us_target

@app.route('/<path:pid>')
def hello_world(pid):
    try:
        parsed = next(ifcb().pid(pid))
    except StopIteration:
        abort(404)
    time_series = parsed['ts_label']
    lid = parsed['lid']
    url_root = request.url_root
    canonical_pid = canonicalize(url_root, time_series, lid)
    try:
        data_roots = list(get_data_roots(time_series))
    except NotFound:
        abort(404)
    schema_version = parsed['schema_version']
    adc_cols = parsed['adc_cols'].split(' ')
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
    heft = 'medium' # default heft for JSON representations
    if 'extension' in parsed:
        extension = parsed['extension']
    if 'target' in parsed:
        canonical_bin_pid = canonicalize(url_root, time_series, parsed['bin_lid'])
        target_no = parsed['target']
        target = adc.get_target(target_no)
        add_pid(target, canonical_bin_pid)
        if extension == 'json':
            return Response(json.dumps(target),mimetype='application/json')
        # not JSON, look for another target representation MIME type
        mimetype = mimetypes.types_map['.' + extension]
        if mimetype.startswith('image/'):
            img = read_target_image(target, roi_path)
            return Response(as_bytes(img,mimetype),mimetype=mimetype)
    else: # bin
        if extension in ['hdr', 'adc', 'roi']:
            path = dict(hdr=hdr_path, adc=adc_path, roi=roi_path)[extension]
            mimetype = dict(hdr='text/plain', adc='text/csv', roi='application/octet-stream')[extension]
            return Response(file(path), direct_passthrough=True, mimetype=mimetype)
        if extension=='csv':
            targets = get_targets(adc, canonical_pid)
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines)+'\n',mimetype='text/csv')
        # we'll need the header for the other representations
        hdr = parse_hdr_file(hdr_path)
        # and the timestamp
        timestamp = iso8601(strptime(parsed['timestamp'], parsed['timestamp_format']))
        if extension=='json':
            targets = get_targets(adc, canonical_pid)
            return Response(bin2json(canonical_pid,hdr,targets,timestamp),mimetype='application/json')
        if extension=='xml':
            targets = get_targets(adc, canonical_pid)
            return Response(bin2xml(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
        if extension=='rdf':
            targets = get_targets(adc, canonical_pid)
            return Response(bin2rdf(canonical_pid,hdr,targets,timestamp),mimetype='text/xml')
    return 'unimplemented'

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=True)
