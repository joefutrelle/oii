import numpy as np
from numpy import random
from numpy.linalg import eig
from scipy import stats, signal, optimize
from scipy.spatial.distance import cdist, euclidean

def index_normalize(arr):
    if arr.size==0:
        return np.array([]), np.array([])
    # normalize and return 0-1 index array
    return np.linspace(0,1,arr.size), (arr - np.min(arr)) / np.ptp(arr)
    
def get_distance_histogram(X, Y):
    # compute distances from centroid
    centroid = [np.mean(X), np.mean(Y)]
    P = np.vstack((X,Y)).T
    C = np.array([centroid])
    D = cdist(P,C,'euclidean').flatten()
    # sorted distance
    D = np.sort(D)
    # normalized distance
    i, D = index_normalize(D)
    return i, D

def camera_spot(i, D):
    # split the distance histogram at the elbow between its linear
    # region and its exponential region
    elbow = np.argmin(D-i)
    j, Dl = index_normalize(D[elbow:])
    k, Dr = index_normalize(D[:elbow])
    # now compute the mode count for each region and divide by the size
    # of the region. if either mode count is high, that likely indicates
    # a camera spot
    mcl = 1. * stats.mode(Dl)[1][0] / Dl.size
    mcr = 1. * stats.mode(Dr)[1][0] / Dr.size
    return max(mcl, mcr)

def clipping(X, Y):
    # compute a bounding box slightly inside the bounding
    # box of all the points
    xpad = np.ptp(X) * 0.01
    ypad = np.ptp(Y) * 0.01
    ll = np.array([np.min(X) + xpad, np.min(Y) + ypad])
    ur = np.array([np.max(X) - xpad, np.max(Y) - ypad])

    # count the points inside the bounding box
    P = np.vstack((X,Y)).T
    inidx = np.all(np.logical_and(ll <= P, P <= ur), axis=1)
    # there should not be a high percentage of points outside the bbox;
    # if there are, images may be clipped at the edge of the camera field
    return 100. - (100. * np.sum(inidx) / X.size)

def core(X, Y):
    # estimate density at each point
    # but subsample the points because kde is slow
    step = max(1,X.size//1000)
    x, y = X[::step], Y[::step]
    xy = np.vstack([x,y])
    z = stats.gaussian_kde(xy)(xy)
    # select non-outliers
    zix = np.where(z > np.percentile(z,10))
    # compute minimum aspect ratio
    # robust to x/y swap, assumes instrument will not generate
    # horizontal core
    aspect_ratio = 1. * np.ptp(x[zix]) / np.ptp(y[zix])
    return min(aspect_ratio, 1/aspect_ratio)

def get_metrics(X, Y):
    # compute weighted sum of metrics
    i, D = get_distance_histogram(X, Y)  
    cs = camera_spot(i, D)
    clip = clipping(X, Y)
    cr = core(X, Y)
    return {
        "camera_spot": cs,
        "clipping": clip,
        "core_aspect": cr,
        "position": (cs * 10.) + (clip * 0.5) + (cr * 2.5)
    }

def get_flow(targets):
    if not targets: # no ROIs
        return 0 # unable to determine that this is bad flow
    X = np.array([p['left'] for p in targets])
    Y = np.array([p['bottom'] for p in targets])
    # exclude -999
    X = X[np.where(X != -999)]
    Y = Y[np.where(Y != -999)]
    return get_metrics(X, Y)
