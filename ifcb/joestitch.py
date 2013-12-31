import numpy as np
from numpy.random import RandomState

from scipy.ndimage.filters import convolve
from scipy.ndimage.filters import minimum_filter
from scipy.ndimage.filters import gaussian_filter

from skimage import img_as_float

from oii.image.io import as_numpy
from oii.image.morphology import inpaint

from oii.ifcb.stitching import mask as rois_mask
from oii.ifcb.stitching import stitch_raw, stitched_box

def stitch(targets,images):
    mask = rois_mask(targets) # True where image data is
    gaps_mask = mask==False # True where infill needs to go
    # compute bounds relative to the camera field
    (x,y,w,h) = stitched_box(targets)
    uroi = img_as_float(stitch_raw(targets,images,(x,y,w,h))) # stitch with black infill

    # step 1: sparsely sample background mostly ignoring blob
    # compute gradient on both axes
    k = [[-3,-1,0,1,3],
         [-3,-1,0,1,3],
         [-3,-1,0,1,3],
         [-3,-1,0,1,3]]
    gy = convolve(uroi,k)
    gx = convolve(uroi,np.rot90(k))
    # ignore all but low-gradient areas
    bg = (abs(gy+gx) < 0.2) & mask

    # step 2: remove less contiguous areas
    filter_size = max(2,int(max(h,w)/200))
    mf = minimum_filter(bg*1,filter_size)

    # step 3: interpolate between samples
    z = inpaint(uroi*mf,mf==False)

    # step 4: subsample and re-interpolate to degrade artifacts in fill region
    random = RandomState(0)
    (h,w)=z.shape
    ng = random.rand(h,w) < 0.01
    z2 = inpaint(z*ng,ng==False)

    # step 5: final composite
    roi = (z2 * gaps_mask) + uroi
    return (roi * 255).astype(np.uint8), mask

