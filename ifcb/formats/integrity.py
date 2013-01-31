import os
import sys
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
    try:
        (prev_bottom, prev_left, prev_trigger) = (None, None, None)
        for target in read_adc(adc_source, schema_version=schema_version):
            (bottom, left, trigger) = (target[BOTTOM], target[LEFT], target[TRIGGER])
            if (bottom, left, trigger) == (prev_bottom, prev_left, prev_trigger):
                logging.warn('.adc stitched pair co-located')
            (prev_bottom, prev_left, prev_trigger) = (bottom, left, trigger)
            yield target
    except Exception, e:
        raise IntegrityException('.adc failed: ' + str(e)), None, sys.exc_info()[2]

def check_roi(roi_source, targets):
    pos = 1
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
            # skip to next target
            skip = target[BYTE_OFFSET] - pos
            if skip < 0:
                raise IntegrityException('.roi byte offsets non-monotonic')
            read_n(fin, skip)
            pos += skip
            # now read the image data for this target
            target_size = target[HEIGHT] * target[WIDTH]
            target_data = read_n(fin, target_size)
            pos += target_size

def check_all(hdr_source, adc_source, roi_source, schema_version=SCHEMA_VERSION_2):
    check_hdr(hdr_source)
    logging.info('hdr check PASSED')
    targets = list(check_adc(adc_source, schema_version=schema_version))
    logging.info('adc check PASSED')
    check_roi(roi_source, targets)
    logging.info('roi check PASSED')

def doit():
    for hdr_file in sorted(glob('/data/vol3/IFCB1_2008_*/*.hdr')):
        lid = remove_extension(os.path.basename(hdr_file))
        logging.info('checking %s' % lid)
        hdr_source = LocalFileSource(hdr_file)
        adc_source = LocalFileSource(change_extension(hdr_file, 'adc'))
        roi_source = LocalFileSource(change_extension(hdr_file, 'roi'))
        check_all(hdr_source, adc_source, roi_source, schema_version=SCHEMA_VERSION_1)

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    doit()
