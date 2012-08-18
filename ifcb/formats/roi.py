from oii.io import PartSource
from oii.ifcb.formats.adc import BYTE_OFFSET, WIDTH, HEIGHT
from PIL import Image
from array import array
from StringIO import StringIO

ROI='roi'

def read_roi(source, target):
    """target should be a dictionary containing BYTE_OFFSET, WIDTH, and HEIGHT,
    i.e., the output of read_adc,
    source is any openable stream or Source"""
    offset = target[BYTE_OFFSET]
    w = target[WIDTH]
    h = target[HEIGHT]
    size = w * h
    if size == 0:
        raise KeyError('no ROI data for target')
    else:
        with PartSource(source,offset,size) as part:
            return Image.fromstring('L', (h, w), part.getvalue()) # rotate 90 degrees

def read_rois(targets,roi_path=None,roi_file=None):
    """roi_path = pathname of ROI file,
    roi_file = already open ROI file"""
    if roi_file is None:
        fp = open(roi_path,'rb')
    else:
        fp = roi_file
    for target in sorted(targets, key=lambda t: t[BYTE_OFFSET]):
        w = target[WIDTH]
        h = target[HEIGHT]
        size = w * h
        if size == 0:
            yield None
        else:
            fp.seek(target[BYTE_OFFSET])
            yield Image.fromstring('L', (h, w), StringIO(fp.read(size)).getvalue()) # rotate 90 degrees
    if roi_path is not None:
        fp.close()

            
    
    
