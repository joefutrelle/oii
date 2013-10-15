import numpy as np

from scipy.ndimage.filters import generic_filter, gaussian_filter

from skimage.exposure import rescale_intensity
from skimage.morphology import square

def unsharp_mask(image,size,a=3):
    um = gaussian_filter(image,size)
    return (a / (a - 1)) * (image - um / a)

def contrast_stretch(image,amount=2):
    """
    Increase global contrast via histogram stretching.

    Parameters
    ----------
    amount : int between 0 and 100
        Percentile of histogram to treat as black (and inverse of percentile
        to treat as white)
    """
    low = np.percentile(image,amount)
    high = np.percentile(image,100-amount)
    return rescale_intensity(image,in_range=(low,high))

def local_variance(image,footprint=square(3),mode='reflect',cval=0.0):
    """warning: slow"""
    return generic_filter(image, np.var, footprint=footprint, mode=mode,cval=cval)
