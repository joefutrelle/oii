from sqlalchemy.exc import InvalidRequestError

from oii.ifcb2 import get_resolver, FILE_PATH, TS_LABEL
from oii.ifcb2.identifiers import parse_pid, PRODUCT
from oii.ifcb2.orm import DataDirectory, TimeSeries

from oii.ldr import pprint

class NotFound(Exception):
    pass

def pid2fileset(pid,roots):
    parsed_pid = parse_pid(pid)
    return parsed_pid2fileset(parsed_pid,roots)

def parsed_pid2fileset(parsed_pid,roots):
    paths = {}
    for root in roots:
        try:
            p = next(get_resolver().ifcb.files.find_raw_fileset(root=root,**parsed_pid))
            paths.update(p)
            if paths:
                return paths
        except StopIteration:
            pass # try the next one
    # we tried all roots and it's not there
    raise NotFound('No raw data found for %s' % parsed_pid['bin_lid'])

def get_data_roots(session, ts_label, product_type='raw'):
    """get the data roots for a given time series label. requires an ORM session"""
    # this needs to be protected with session management
    dds = session.query(DataDirectory)\
                 .join(TimeSeries)\
                 .filter(TimeSeries.label==ts_label)\
                 .filter(DataDirectory.product_type==product_type)
    return [dd.path for dd in dds]

def get_product_destination(session, pid, product_type=None):
    parsed = parse_pid(pid)
    if product_type is None:
        product_type = parsed[PRODUCT]
    ts_label = parsed[TS_LABEL]
    if product_type=='multiblob': # sidecar files for features
        product_type='features'
    roots = get_data_roots(session, ts_label, product_type=product_type)
    if not roots:
        raise NotFound('no product destination found')
    root = roots[0]
    S = next(get_resolver().ifcb.files.product_path(root=root,**parsed))
    return S[FILE_PATH]
