import numpy as np
import struct
from array import array

from oii.ifcb2.formats.adc import BYTE_OFFSET, HEIGHT, WIDTH

def read_roi_image(byte_offset, width, height, roi_file):
    length = width * height
    image_data = array('B')
    with open(roi_file,'rb') as raf:
        raf.seek(byte_offset)
        image_data.fromfile(raf,length)
    return np.array(image_data, dtype=np.uint8).reshape((width,height))

def read_target_image(parsed_target, roi_file):
    return read_roi_image(parsed_target[BYTE_OFFSET], parsed_target[WIDTH], parsed_target[HEIGHT], roi_file)
