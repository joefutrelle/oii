from jinja2 import Environment

from oii.csvio import csv_str, csv_quote
from oii.ifcb2.identifiers import PID
from oii.ifcb2.formats.adc import TARGET_NUMBER

def targets2csv(targets,schema_cols,headers=True):
    """Given targets, produce a CSV representation in the specified schema;
    targets should have had binID and pid added to them (see oii.ifcb2.identifiers)"""
    ks = schema_cols + ['binID','pid','stitched','targetNumber']
    if headers:
        yield ','.join(ks)
    for target in targets:
        # fetch all the data for this row as strings, emit
        yield ','.join(csv_quote(csv_str(target[k])) for k in ks)

BIN_XML_TEMPLATE = """<Bin xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://ifcb.whoi.edu/terms#">
  <dc:identifier>{{pid}}</dc:identifier>
  <dc:date>{{timestamp}}</dc:date>{% for v in context %}
  <context>{{v}}</context>{% endfor %}{% for k,v in properties %}
  <{{k}}>{{v}}</{{k}}>{% endfor %}{% for target_pid in target_pids %}
  <Target dc:identifier="{{target_pid}}"/>{% endfor %}
</Bin>
"""

def bin2xml(pid,hdr,targets,timestamp):
    """pid should be the bin pid (with namespace)
    timestamp should be a text timestamp in iso8601 format
    hdr should be the result of calling parse_hdr on a header file
    targets should be a list of target dicts with target names"""
    context = hdr['context']
    properties = [(k,v) for k,v in hdr.items() if k != 'context']
    target_pids = [target[PID] for target in targets]
    kvs = dict(pid=pid,timestamp=timestamp,context=context,properties=properties,target_pids=target_pids)
    return Environment().from_string(BIN_XML_TEMPLATE).render(**kvs)
