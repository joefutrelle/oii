from oii.io import PartSource
from oii.ifcb.formats.adc import BYTE_OFFSET, WIDTH, HEIGHT
from PIL import Image
from array import array

def read_roi(source, target):
    """target should be a dictionary containing BYTE_OFFSET, WIDTH, and HEIGHT,
    i.e., the output of read_adc"""
    offset = target[BYTE_OFFSET]
    w = target[WIDTH]
    h = target[HEIGHT]
    size = w * h
    if size == 0:
        raise KeyError('no ROI data for target')
    else:
        with PartSource(source,offset,size) as part:
            return Image.fromstring('L', (h, w), part.getvalue()) # rotate 90 degrees
            
    
    
