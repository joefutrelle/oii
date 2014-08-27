import numpy as np
import struct
from array import array

from oii.ifcb2.formats.adc import BYTE_OFFSET, HEIGHT, WIDTH

def read_roi_image(byte_offset, width, height, open_roi_file):
    length = width * height
    image_data = array('B')
    open_roi_file.seek(byte_offset)
    image_data.fromfile(open_roi_file,length)
    return np.array(image_data, dtype=np.uint8).reshape((width,height))

def read_target_image(parsed_target, path=None, file=None):
    if path is not None:
        with open(path,'rb') as open_roi_file:
            return read_roi_image(parsed_target[BYTE_OFFSET], parsed_target[WIDTH], parsed_target[HEIGHT], open_roi_file)
    else:
        return read_roi_image(parsed_target[BYTE_OFFSET], parsed_target[WIDTH], parsed_target[HEIGHT], file)
