"""Define helper utilities for iPython for displaying images.
This is to avoid using the cumbersome matplotlib API"""
import os
from tempfile import mkstemp

import numpy as np

from scipy.ndimage import measurements
from skimage import img_as_float
from skimage.io import imsave
from skimage.color import hsv2rgb
from skimage.exposure import rescale_intensity
from skimage.segmentation import find_boundaries

from IPython.core import display

from oii.image.transform import resize, rescale

def tmp_img(extension='.png',tmpdir='tmp'):
    if not os.path.exists(tmpdir):
        try:
            os.makedirs(tmpdir)
        except:
            pass
        assert os.path.exists(tmpdir)
    (o,f) = mkstemp(suffix=extension,dir=tmpdir)
    os.close(o)
    return f

def show_image(image,max_width=None):
    f = tmp_img()
    if max_width is not None:
        (h,w) = image.shape[:2]
        scale = max_width / float(w)
        image = rescale(image,scale)
    if image.dtype == np.bool:
        image = image.astype(np.int) * 255
    imsave(f,image)
    return display.Image(filename=f)

def as_spectrum(gray):
    One = np.ones(gray.shape,np.float)
    Y = 1 - rescale_intensity(img_as_float(gray))
    HSV = np.dstack([Y*0.66,One,One])
    return hsv2rgb(HSV)

def show_spectrum(gray):
    return show_image(as_spectrum(gray))

def as_masked(rgb,mask,outline=False):
    copy = img_as_float(rgb,force_copy=True)
    if outline:
        (labels,_) = measurements.label(mask)
        boundaries = find_boundaries(labels)
        copy[boundaries] = [1,0,0]
    else:
        copy[mask] = [1,0,0]
    return copy

def show_masked(rgb,mask,outline=False):
    return show_image(as_masked(rgb,mask,outline))
