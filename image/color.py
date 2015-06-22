import numpy as np

from skimage.color import gray2rgb, rgb2hsv, hsv2rgb, rgb2gray

def gray_value(a):
    # computes grayworld gray value
    (_,_,c) = a.shape
    means = [np.mean(a[:,:,n]) for n in range(c)]
    return np.mean(means)

def gray_world(a,gray=None):
    """Gray-world color balance"""
    (_,_,c) = a.shape
    means = [np.mean(a[:,:,n]) for n in range(c)]
    if gray is None:
        gray = np.mean(means)
    return a * (gray / means)

def scale_saturation(a,saturation=1.0):
    hsv = rgb2hsv(a)
    hsv[:,:,1] = (hsv[:,:,1] * saturation).clip(0.,1.)
    return hsv2rgb(hsv)
