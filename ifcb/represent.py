import sys
import re
import shutil
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import tempfile
from copy import deepcopy
import numpy as np
from scipy.io import loadmat

from jinja2 import Environment

from oii.resolver import parse_stream
from oii.iopipes import LocalFileSource, StagedInputFile, UrlSource, LocalFileSink, drain

from oii.ifcb.formats.adc import read_adc, ADC_SCHEMA, TARGET_NUMBER, SCHEMA_VERSION_2
from oii.ifcb.formats.hdr import read_hdr, HDR, CONTEXT, HDR_SCHEMA
from oii.ifcb.stitching import find_pairs, stitch, stitched_box, stitch_raw, list_stitched_targets
from oii.ifcb.formats.roi import read_roi, read_rois, ROI

PID='pid'

def add_bin_pid(targets, bin_pid):
    for target in targets:
        # add a binID and pid what are the right keys for these?
        target['binID'] = '%s' % bin_pid
        target['pid'] = '%s_%05d' % (bin_pid, target[TARGET_NUMBER])
    return targets

def im2bytes(im):
    buf = BytesIO()
    with tempfile.SpooledTemporaryFile() as imtemp:
        im.save(imtemp,'PNG')
        imtemp.seek(0)
        shutil.copyfileobj(imtemp, buf)
    return buf.getvalue()

def csv_quote(thing):
    if re.match(r'^-?[0-9]+(\.[0-9]+)?$',thing):
        return thing
    else:
        return '"' + thing + '"'

def csv_str(v):
    try:
        return re.sub(r'\.$','',('%.12f' % v).rstrip('0'))
    except:
        return str(v)

def bin2csv(targets,schema_version=SCHEMA_VERSION_2):
    ks = [k for k,_ in ADC_SCHEMA[schema_version]] + ['binID','pid','stitched','targetNumber']
    yield ','.join(ks)
    for target in targets:
        # fetch all the data for this row as strings, emit
        yield ','.join(csv_quote(csv_str(target[k])) for k in ks)

BIN_XML_TEMPLATE = """
<Bin xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://ifcb.whoi.edu/terms#">
  <dc:identifier>{{hit.bin_pid}}</dc:identifier>
  <dc:date>{{hit.date}}</dc:date>{% for v in context %}
  <context>{{v}}</context>{% endfor %}{% for k,v in properties %}
  <{{k}}>{{v}}</{{k}}>{% endfor %}{% for target_pid in target_pids %}
  <Target dc:identifier="{{target_pid}}"/>{% endfor %}
</Bin>
"""

def bin2xml(template):
    return Environment().from_string(BIN_XML_TEMPLATE).render(**template)

def bin_zip(hit, hdr_path, adc_path, roi_path, outfile):
    """hit should be the hit on the mvco resolver for pid=bin_pid on the 'pid' resolver.
    outfile must be a filelike object open for writing, not a pathname. StringIO will work"""
    props = read_hdr(LocalFileSource(hdr_path))
    context = props[CONTEXT]
    del props[CONTEXT]
    props = [(k,props[k]) for k,_ in HDR_SCHEMA if k in props]

    raw_targets = list(read_adc(LocalFileSource(adc_path), 1, -1, hit.schema_version))
    raw_targets = add_bin_pid(raw_targets, hit.bin_pid)
    stitched_targets = deepcopy(raw_targets)
    stitched_targets = list_stitched_targets(stitched_targets)
    stitched_targets = add_bin_pid(stitched_targets, hit.bin_pid)
    target_pids = ['%s_%05d' % (hit.bin_pid, target['targetNumber']) for target in stitched_targets]
    template = dict(hit=hit,context=context,properties=props,targets=stitched_targets,target_pids=target_pids)

    with tempfile.SpooledTemporaryFile() as temp:
        z = ZipFile(temp,'w',ZIP_DEFLATED)
        csv_out = '\n'.join(bin2csv(stitched_targets, hit.schema_version))
        z.writestr(hit.bin_lid + '.csv', csv_out)
        # xml as well, including header info
        z.writestr(hit.bin_lid + '.xml', bin2xml(template))
        pairs = list(find_pairs(raw_targets))
        with open(roi_path,'rb') as roi_file:
            for target in stitched_targets:
                im = None
                for (a,b) in pairs:
                    if a[TARGET_NUMBER] == target[TARGET_NUMBER]:
                        images = list(read_rois((a,b),roi_file=roi_file)) # read the images
                        (im, _) = stitch((a,b), images) # stitch them
                if im is None:
                    im = list(read_rois([target],roi_file=roi_file))[0] # read the image
                # need LID here
                target_lid = re.sub(r'.*/','',target[PID]) # FIXME resolver should do this
                z.writestr(target_lid + '.png', im2bytes(im))
        z.close()
        temp.seek(0)
        shutil.copyfileobj(temp, outfile)

def binpid2zip(bin_pid, outfile, resolver_file='oii/ifcb/mvco.xml', resolver=None):
    if resolver is None:
        resolver = parse_stream(resolver_file)
    hit = resolver['pid'].resolve(pid=bin_pid)
    with tempfile.NamedTemporaryFile() as hdr:
        hdr_path = hdr.name
        drain(UrlSource(bin_pid+'.hdr'), LocalFileSink(hdr_path))
        with tempfile.NamedTemporaryFile() as adc:
            adc_path = adc.name
            drain(UrlSource(bin_pid+'.adc'), LocalFileSink(adc_path))
            with tempfile.NamedTemporaryFile() as roi:
                roi_path = roi.name
                drain(UrlSource(bin_pid+'.roi'), LocalFileSink(roi_path))
                bin_zip(hit, hdr_path, adc_path, roi_path, outfile)

def classmat2csv(matfile, bin_lid):
    mat = loadmat(matfile)

    scores = mat['TBscores'] # score matrix (roi x scores)
    labels = mat['class2useTB'] # class labels
    roinum = mat['roinum'] # roi num for each row

    def matlabels2strs(labels):
        return [l.astype(str)[0] for l in labels[:,0]]

    yield ','.join(['pid'] + matlabels2strs(labels))

    for roi, row in zip(roinum[:,0], scores[:]):
        fmt = ['"%s_%05d"' % (bin_lid, roi)] + [re.sub(r'000$','','%.4f' % c) for c in row.tolist()]
        yield ','.join(fmt)
