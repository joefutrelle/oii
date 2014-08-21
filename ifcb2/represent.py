from jinja2 import Environment
import json

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

def _split_hdr(parsed_hdr):
    context = parsed_hdr['context']
    properties = [(k,v) for k,v in parsed_hdr.items() if k != 'context']
    return context, properties

def _get_bin_template_bindings(pid,hdr,targets,timestamp):
    """pid should be the bin pid (with namespace)
    timestamp should be a text timestamp in iso8601 format
    hdr should be the result of calling parse_hdr on a header file
    targets should be a list of target dicts with target pids"""
    context, properties = _split_hdr(hdr)
    target_pids = [target[PID] for target in targets]
    return dict(pid=pid,timestamp=timestamp,context=context,properties=properties,target_pids=target_pids)

def bin2xml(pid,hdr,targets,timestamp):
    """pid should be the bin pid (with namespace)
    timestamp should be a text timestamp in iso8601 format
    hdr should be the result of calling parse_hdr on a header file
    targets should be a list of target dicts with target pids"""
    bindings = _get_bin_template_bindings(pid,hdr,targets,timestamp)
    return Environment().from_string(BIN_XML_TEMPLATE).render(**bindings)

BIN_RDF_TEMPLATE = """<rdf:RDF xmlns:dcterms="http://purl.org/dc/terms/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://ifcb.whoi.edu/terms#">
  <Bin rdf:about="{{pid}}">
    <dc:date>{{timestamp}}</dc:date>{% for v in context %}
    <context>{{v}}</context>{% endfor %}{% for k,v in properties %}
    <{{k}}>{{v}}</{{k}}>{% endfor %}
    <dcterms:hasPart>
      <rdf:Seq rdf:about="{{pid}}/targets">{% for target_pid in target_pids %}
        <rdf:li>
          <Target rdf:about="{{target_pid}}"/>
        </rdf:li>{% endfor %}
      </rdf:Seq>
    </dcterms:hasPart>
  </Bin>
</rdf:RDF>"""

def bin2rdf(pid,hdr,targets,timestamp):
    """pid should be the bin pid (with namespace)
    timestamp should be a text timestamp in iso8601 format
    hdr should be the result of calling parse_hdr on a header file
    targets should be a list of target dicts with target pids"""
    bindings = _get_bin_template_bindings(pid,hdr,targets,timestamp)
    return Environment().from_string(BIN_RDF_TEMPLATE).render(**bindings)

def bin2dict_short(pid,hdr,timestamp):
    context, rep = _split_hdr(hdr)
    rep = dict(rep)
    rep['context'] = context
    rep['date'] = timestamp
    rep['pid'] = pid
    return rep

def bin2dict_medium(pid,hdr,targets,timestamp):
    rep = bin2dict_short(pid,hdr,timestamp)
    rep['targets'] = [target[PID] for target in targets]
    return rep

def bin2dict(pid,hdr,targets,timestamp):
    rep = bin2dict_short(pid,hdr,timestamp)
    rep['targets'] = list(targets)
    return rep

def bin2json_short(pid,hdr,timestamp):
    return json.dumps(bin2dict_short(pid,hdr,timestamp))

def bin2json_medium(pid,hdr,targets,timestamp):
    return json.dumps(bin2dict_medium(pid,hdr,targets,timestamp))

def bin2json(pid,hdr,targets,timestamp):
    return json.dumps(bin2dict(pid,hdr,targets,timestamp))
