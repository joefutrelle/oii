import numpy as np
import numpy.ma as ma

from oii.image.io import imread_float, imsave_clip
from oii.image.color import rgb2gray

from scipy.ndimage.filters import minimum_filter

from skimage.morphology import square

"""
Dehazing based on

Single Image Haze Removal Using Dark Channel Prior
Kaiming He, Jian Sun, Xiaoou Tang

http://research.microsoft.com/en-us/um/people/jiansun/papers/Dehaze_CVPR2009.pdf
"""
def dark_channel(image,structure=square(15)):
    (h,w,c) = image.shape
    dark_channels = np.zeros_like(image)
    for i in range(c):
        dark_channels[:,:,i] = minimum_filter(image[:,:,i],footprint=structure)
    dark_channel = np.min(dark_channels,axis=2)
    return dark_channel

def haze_mask(dark_channel):
    return dark_channel > np.percentile(dark_channel,99.9)

def estimate_light(image,dark_channel):
    Y = rgb2gray(image)
    masked = ma.array(Y,haze_mask(dark_channel))
    (h,w) = np.unravel_index(ma.argmax(masked),Y.shape)
    light = image[h,w,:]
    return light

def dehaze(rgb,structure=square(3)):
    dc = dark_channel(rgb,structure=structure)
    A = estimate_light(rgb,dc)
    IoverA = rgb / A
    t = 1. - dark_channel(IoverA,structure=structure)
    # FIXME now need to apply soft masking
    (h,w,_) = rgb.shape
    Am = np.ones((h,w,3)) * A
    tm = np.dstack([t,t,t])
    J = ((rgb - Am) / tm) + Am
    return Am
