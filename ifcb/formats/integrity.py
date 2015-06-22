import os
import sys
import re
from glob import glob
import logging

from oii.utils import remove_extension, change_extension
from oii.iopipes import LocalFileSource
from oii.ifcb.formats.hdr import read_hdr
from oii.ifcb.formats.adc import read_adc, SCHEMA_VERSION_1, SCHEMA_VERSION_2, TRIGGER, BOTTOM, LEFT, BYTE_OFFSET, HEIGHT, WIDTH

class IntegrityException(Exception):
    pass

def check_hdr(hdr_source):
    try:
        read_hdr(hdr_source)
    except Exception, e:
        raise IntegrityException('.hdr failed: ' + str(e)), None, sys.exc_info()[2]

def check_adc(adc_source, schema_version=SCHEMA_VERSION_2):
    def gen_targets():
        (prev_bottom, prev_left, prev_trigger) = (None, None, None)
        (pairs, colocated_pairs) = (0, 0)
        for target in read_adc(adc_source, schema_version=schema_version):
            (bottom, left, trigger) = (target[BOTTOM], target[LEFT], target[TRIGGER])
            if trigger == prev_trigger:
                pairs += 1
            if (bottom, left, trigger) == (prev_bottom, prev_left, prev_trigger):
                colocated_pairs += 1
            (prev_bottom, prev_left, prev_trigger) = (bottom, left, trigger)
            yield target
        if pairs > 0 and pairs == colocated_pairs:
            raise IntegrityException('.adc stitching problem')
    try:
        # call list(gen_targets()) so that it can raise an exception
        # before any target is yielded
        for target in list(gen_targets()):
            yield target
    except Exception, e:
        raise IntegrityException('.adc failed: ' + str(e)), None, sys.exc_info()[2]

def check_roi(roi_source, targets):
    pos = -1
    def read_n(fin, n):
        try:
            r = fin.read(n)
        except Exception, e:
            raise IntegrityException('unable to read roi data: '+str(e)), None, sys.exc_info()[2]
        if len(r) != n:
            raise IntegrityException('roi file truncated')
        return r
    with roi_source as fin:
        for target in targets:
            if pos == -1:
                pos = target[BYTE_OFFSET]
            # skip to next target
            skip = target[BYTE_OFFSET] - pos
            if skip < 0:
                raise IntegrityException('.roi byte offsets non-monotonic: %d < %d' % (target[BYTE_OFFSET], pos))
            read_n(fin, skip)
            pos += skip
            # now read the image data for this target
            target_size = target[HEIGHT] * target[WIDTH]
            target_data = read_n(fin, target_size)
            pos += target_size

def check_all(lid, hdr_source, adc_source, roi_source, schema_version=SCHEMA_VERSION_2):
    check_hdr(hdr_source)
    logging.info('%s PASS hdr' % lid)
    targets = list(check_adc(adc_source, schema_version=schema_version))
    logging.info('%s PASS adc' % lid)
    check_roi(roi_source, targets)
    logging.info('%s PASS roi' % lid)

def check_fileset(hdr_file, schema_version=SCHEMA_VERSION_2):
    lid = remove_extension(os.path.basename(hdr_file))
    hdr_source = LocalFileSource(hdr_file)
    adc_file = change_extension(hdr_file, 'adc')
    adc_source = LocalFileSource(adc_file)
    roi_source = LocalFileSource(change_extension(hdr_file, 'roi'))
    try:
        check_all(lid, hdr_source, adc_source, roi_source, schema_version=schema_version)
        logging.info('%s PASS ALL' % lid)
    except IntegrityException, e:
        logging.info('%s FAIL %s' % (lid, e))
        raise

def doit():
    for hdr_file in sorted(glob('/data/vol3/IFCB1_2008_*/*.hdr')):
        check_fileset(hdr_file, schema_version=SCHEMA_VERSION_1)

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    doit()
