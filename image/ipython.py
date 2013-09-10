"""Define helper utilities for iPython for displaying images.
This is to avoid using the cumbersome matplotlib API"""
import os
from tempfile import mkstemp

import numpy as np

from scipy.ndimage import measurements
from skimage.io import imsave
from skimage.color import hsv2rgb
from skimage.exposure import rescale_intensity
from skimage.segmentation import find_boundaries

from IPython.core import display

def tmp_img(extension='.png'):
    (o,f) = mkstemp(suffix=extension,dir='tmp')
    os.close(o)
    return f

def show_image(image):
    f = tmp_img()
    imsave(f,image)
    return display.Image(filename=f)

def show_spectrum(gray):
    One = np.ones_like(gray)
    HSV = np.dstack([(1-gray)*0.66,One,One])
    RGB = hsv2rgb(HSV)
    return show_image(RGB)

def show_masked(rgb,mask,outline=False):
    copy = img_as_float(rgb,force_copy=True)
    if outline:
        (labels,_) = measurements.label(mask)
        boundaries = find_boundaries(labels)
        copy[boundaries] = [1,0,0]
    else:
        copy[mask] = [1,0,0]
    return show_image(copy)
