import sys
import os
import logging

from oii.utils import remove_extension
from oii.ifcb2 import HDR, ADC, ROI
from oii.ifcb2.formats.hdr import parse_hdr_file
from oii.ifcb2.formats.adc import Adc, TRIGGER, BOTTOM, LEFT, SCHEMA_VERSION_2, BYTE_OFFSET, WIDTH, HEIGHT

class IntegrityException(Exception):
    pass

def check_hdr(hdr_path):
    try:
        parse_hdr_file(hdr_path)
    except Exception, e:
        raise IntegrityException('.hdr failed: ' + str(e)), None, sys.exc_info()[2]

def check_adc(adc_path, schema_version=SCHEMA_VERSION_2):
    adc = Adc(adc_path, schema_version)
    def gen_targets():
        (prev_bottom, prev_left, prev_trigger) = (None, None, None)
        (pairs, colocated_pairs) = (0, 0)
        for target in adc.get_targets():
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
        return list(gen_targets())
    except Exception, e:
        raise IntegrityException('.adc failed: ' + str(e)), None, sys.exc_info()[2]

def check_roi(roi_path, targets):
    roi_length = os.path.getsize(roi_path)
    pos = -1
    for target in targets:
        if pos == -1:
            pos = target[BYTE_OFFSET]
        # skip to next target
        skip = target[BYTE_OFFSET] - pos
        if skip < 0:
            raise IntegrityException('.roi byte offsets non-monotonic: %d < %d' % (target[BYTE_OFFSET], pos))
        pos += skip
        target_size = target[HEIGHT] * target[WIDTH]
        pos += target_size
        if pos > roi_length:
            raise IntegrityException('.roi byte offset longer than ROI file: %d > %d' % (pos, roi_length))

def check_fileset(fileset, schema_version=SCHEMA_VERSION_2):
    hdr_path = fileset[HDR]
    adc_path = fileset[ADC]
    roi_path = fileset[ROI]
    lid = remove_extension(os.path.basename(hdr_path))
    try:
        check_hdr(hdr_path)
        logging.info('PASS %s hdr %s' % (lid, hdr_path))
        targets = check_adc(adc_path, schema_version=schema_version)
        logging.info('PASS %s adc %s' % (lid, adc_path))
        check_roi(roi_path, targets)
        logging.info('PASS %s roi %s' % (lid, roi_path))
    except IntegrityException, e:
        logging.info('%s FAIL %s' % (lid, e))
        raise


