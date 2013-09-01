import numpy as np

from scipy import ndimage
from skimage.morphology import binary_dilation

EIGHT = np.ones((3,3))

def hysthresh(img,T1,T2):
    T2,T1 = sorted([T1,T2])
    c = np.ones((3,3))
    edges = np.where(img > T1,1,0)
    bd = np.where((binary_dilation(edges,EIGHT) - edges) * img > T2,1,0)
    return np.where(edges + bd > 0,1,0)

def bwmorph_thin(img,n_iter=0):
    # http://www.mathworks.com/help/images/ref/bwmorph.html#f1-500491
    # code adapted from skimage.morphology.skeletonize
    # FIXME support infinite iteration
    LUT=[0,0,0,0,0,1,0,1,0,0,0,0,0,1,3,1,0,0,0,0,2,0,2,0,0,0,
         0,0,3,1,3,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
         2,0,2,0,2,0,0,0,2,0,2,0,0,1,0,1,0,1,0,1,0,0,0,0,0,1,
         0,1,2,0,0,0,2,0,2,0,2,0,0,0,2,0,2,0,0,1,0,1,0,1,0,1,
         0,0,0,0,0,0,0,0,2,0,0,0,2,0,2,0,2,0,0,0,2,0,2,0,0,0,
         0,1,0,1,0,1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,
         0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
         0,0,0,0,0,0,0,0,0,0,0,3,0,1,0,1,0,1,0,0,0,0,0,1,0,1,
         2,2,0,0,2,0,0,0,2,2,0,0,2,0,0,0,3,3,0,1,0,1,0,1,0,0,
         0,0,0,0,0,0,2,2,0,0,2,0,0,0,2,2,0,0,2,0,0,0]
    mask = np.array([[ 1, 2, 4],
                     [128, 0, 8],
                     [ 64, 32, 16]], np.uint8)

    skeleton = np.array(img).astype(np.uint8)
    
    done = False
    while(not(done)):
        # assign each pixel a unique value based on its foreground neighbours
        neighbours = ndimage.correlate(skeleton, mask, mode='constant')
        # ignore background
        neighbours *= skeleton
        # use LUT to extract code for deletion stages of thinning algorithm
        codes = np.take(LUT, neighbours)

        done = True
        # pass 1 - remove the 1's
        code_mask = (codes == 1)
        if np.any(code_mask):
            done = False
            skeleton[code_mask] = 0

        neighbours = ndimage.correlate(skeleton, mask, mode='constant')
        # ignore background
        neighbours *= skeleton
        # use LUT to extract code for deletion stages of thinning algorithm
        codes = np.take(LUT, neighbours)

        # pass 2, delete the 2's
        code_mask = (codes > 1)
        if np.any(code_mask):
            done = False
            skeleton[code_mask] = 0

        n_iter -= 1
        if n_iter == 0:
            done = True

    return skeleton

def remove_small_objects(img,min_area,structure=EIGHT):
    (labeled,_) = measurements.label(blob,structure=structure)
    objects = measurements.find_objects(labeled)
    for o in objects:
        area = len(np.where(labeled[o] > 0)[0])
        if area < min_area:
            labeled[o] = np.where(labeled[o] > 0,0,labeled[o])
    return np.where(labeled > 0,1,0)

