import numpy as np

from numpy.random import RandomState

from scipy import ndimage
from scipy.ndimage import measurements
from scipy.ndimage.filters import maximum_filter
from scipy.interpolate import griddata
from scipy.cluster.vq import kmeans2

from skimage.segmentation import find_boundaries
from skimage.morphology import binary_dilation

from sklearn.mixture import GMM

EIGHT = np.ones((3,3))
FOUR = np.array([[0, 1, 0],
                 [1, 1, 1],
                 [0, 1, 0]])

def gmm_threshold(gray):
    """
    Compute GMM model with two gaussians,
    then threshold halfway between the two means
    """
    samples = gray.reshape((gray.size, 1))
    model = GMM(n_states=2, cvtype='full').fit(samples)
    return gray > np.mean(model.means)

def np_random_choice(arr,ns):
    na = np.array(arr)
    return na[np.random.randint(na.size,size=ns)]

def kmeans_threshold(img,n_samples=10000):
    samples = np_random_choice(img.reshape(img.size),n_samples)
    means = [-1,-1]
    while min(means) < 0:
        (means,_) = kmeans2(samples,2)
    means.sort()
    return img > np.mean(means)

def hysthresh(img,T1,T2):
    """All pixels with values above T1 are marked as edges.
    All pixels adjacent to points that have been marked as edges
    and with values above T2 are also marked as edges. Eight-
    connectivity is used.
    Adaopted from Peter Kovesi"""
    T2,T1 = sorted([T1,T2])
    edges = img > T1
    sum = 1
    while sum > 0:
        bd = (binary_dilation(edges,EIGHT) & (img > T2)) - edges
        edges |= bd
        sum = np.sum(bd)
    return edges

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

    return skeleton.astype(np.bool)

def _ro_find(img,structure=EIGHT):
    (labeled,_) = measurements.label(img,structure=structure)
    objects = measurements.find_objects(labeled)
    areas = [len(np.where(labeled[o] > 0)[0]) for o in objects]
    return (labeled,objects,areas)

def remove_small_objects(img,min_area,structure=EIGHT):
    (labeled,objects,areas) = _ro_find(img,structure)
    for label,o,area in zip(range(1,len(objects)+1),objects,areas):
        if area < min_area:
            labeled[labeled == label] = 0
    return labeled > 0

def remove_smallest_objects(img,structure=np.ones((3,3),np.bool),size_range=1.0,max_area=None):
    (labeled,objects,areas) = _ro_find(img,structure)
    if max_area is None:
        max_area = max(areas)
    min_area = min(max_area,(1. * min(areas) * size_range))
    for label,o,area in zip(range(1,len(objects)+1),objects,areas):
        if area <= min_area:
            labeled[labeled == label] = 0
    return labeled > 0

def remove_large_objects(img,max_area,structure=EIGHT):
    (labeled,objects,areas) = _ro_find(img,structure)
    for label,o,area in zip(range(1,len(objects)+1),objects,areas):
        if area > max_area:
            labeled[labeled == label] = 0
    return labeled > 0

def remove_largest_objects(img,structure=np.ones((3,3),np.bool),size_range=1.0,min_area=1):
    (labeled,objects,areas) = _ro_find(img,structure)
    max_area = max(min_area,(1. * max(areas) / size_range))
    for label,o,area in zip(range(1,len(objects)+1),objects,areas):
        if area >= max_area:
            labeled[labeled == label] = 0
    return labeled > 0

def inpaint(img,mask):
    """Inpaint masked regions in an image via linear and
    nearest-neighbor interpolation"""
    random = RandomState(0)
    img = img.astype(np.float)
    def _interp(img,mask,method):
        xi = np.where(mask)
        if len(xi[0])==0:
            return img
        edges = maximum_filter(find_boundaries(mask),3)
        edges[xi] = 0
        yp, xp = np.where(edges)
        values = seed[yp,xp]
        # add jitter to points to avoid https://beagle.whoi.edu/redmine/issues/2609
        yp = np.array(yp) + (random.standard_normal((yp.size)) * 0.0001)
        xp = np.array(xp) + (random.standard_normal((xp.size)) * 0.0001)
        fill = griddata((yp,xp),values,xi,method=method)
        img[xi] = fill
        return img
    seed = img.copy()
    seed = _interp(seed,mask,'linear')
    seed = _interp(seed,np.isnan(seed),'nearest')
    return seed
