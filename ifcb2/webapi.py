from flask import Flask, Response, abort

import mimetypes
import json

from oii.ifcb2 import get_resolver
from oii.ifcb2.files import parsed_pid2fileset
from oii.utils import coalesce, memoize
from oii.image.io import as_bytes
from oii.ifcb2.identifiers import add_pids
from oii.ifcb2.represent import targets2csv
from oii.ifcb2.image import read_target_image
from oii.ifcb2.formats.adc import Adc
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
    paths = []
    for data_dir in ts.data_dirs:
        paths.append(data_dir.path)
        return paths

def get_targets(adc, bin_pid):
    return add_pids(adc.get_targets(),bin_pid)

@app.route('/<path:pid>')
def hello_world(pid):
    try:
        parsed = next(ifcb().pid(pid))
    except StopIteration:
        abort(404)
    time_series = parsed['ns_lid']
    data_roots = list(get_data_roots(time_series))
    schema_version = parsed['schema_version']
    adc_cols = parsed['adc_cols'].split(' ')
    lid = parsed['lid']
    paths = parsed_pid2fileset(parsed,data_roots)
    if not paths:
        abort(404)
    hdr_path = paths['hdr_path']
    adc_path = paths['adc_path']
    roi_path = paths['roi_path']
    adc = Adc(adc_path, schema_version)
    extension = 'json' # default
    heft = 'medium' # default heft for JSON representations
    if 'extension' in parsed:
        extension = parsed['extension']
    if 'target' in parsed:
        target_no = parsed['target']
        target = adc.get_target(target_no)
        if extension == 'json':
            return Response(json.dumps(target),mimetype='application/json')
        # not JSON, look for another target representation MIME type
        mimetype = mimetypes.types_map['.' + parsed['extension']]
        if mimetype.startswith('image/'):
            img = read_target_image(target, roi_path)
            return Response(as_bytes(img,mimetype),mimetype=mimetype)
    else: # bin
        if extension=='csv':
            targets = get_targets(adc, pid)
            lines = targets2csv(targets,adc_cols)
            return Response('\n'.join(lines),mimetype='text/plain') # FIXME text/csv
    return 'unimplemented'

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=True)
