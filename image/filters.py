import numpy as np

from scipy.ndimage.filters import gaussian_filter

from skimage.exposure import rescale_intensity

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
