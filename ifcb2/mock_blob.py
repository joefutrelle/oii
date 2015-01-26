import numpy as np

from skimage import img_as_float
from skimage.exposure import rescale_intensity
from skimage.transform import resize
from skimage.morphology import disk
from scipy.ndimage.filters import generic_filter
from skimage.morphology import reconstruction
from skimage.filter import threshold_otsu

def ifcb_segment(img):
    Y = img_as_float(img)
    # step 1. local variance
    Yv = rescale_intensity(generic_filter(Y, np.var, footprint=disk(3)))
    # step 2. threshold local variance, aggressively
    Ye = Yv > (threshold_otsu(Yv) / 2.)
    # step 3. dark areas
    Yt = Y < threshold_otsu(Y)
    thin_blob = Ye | Yt
    # step 4. morphological reconstruction
    seed = np.copy(thin_blob)
    seed[1:-1,1:-1] = 1
    four=np.disk(1).astype(np.bool)
    return reconstruction(seed,thin_blob,method='erosion',selem=four)
