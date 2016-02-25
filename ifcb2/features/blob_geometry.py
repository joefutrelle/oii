import numpy as np

from numpy.linalg import eig

from scipy.spatial import ConvexHull
from skimage.draw import polygon, line

def blob_area(B):
    return np.sum(np.array(B).astype(np.bool))
    
def blob_extent(B,area=None):
    if area is None:
        area = blob_area(B)
    return float(area) / B.size

def equiv_diameter(area):
    return np.sqrt(4*area/np.pi)

def ellipse_properties(B):
    """returns major axis length, minor axis length, eccentricity,
    and orientation"""
    """note that these values are all computable using
    skimnage.measure.regionprops, which differs only in that
    it returns the orientation in radians"""
    P = np.vstack(np.where(B)) # coords of all points
    # magnitudes and orthonormal basis vectors
    # are computed via the eigendecomposition of
    # the covariance matrix of the coordinates
    eVal, eVec,  = eig(np.cov(P))

    # axes lengths are 4x the sqrt of the eigenvalues,
    # major and minor lenghts are max, min of them
    L = 4 * np.sqrt(eVal)
    maj_axis, min_axis = np.max(L), np.min(L)

    # orientation is derived from the major axis's
    # eigenvector
    x,y = eVec[:, np.argmax(L)]
    orientation = (180/np.pi) * np.arctan(y/x) - 90
    
    # eccentricity = 1st eccentricity
    ecc = np.sqrt(1-(min_axis/maj_axis)**2)
    
    return maj_axis, min_axis, ecc, orientation

def invmoments(B):
    """compute invariant moments. see
    Digital Image Processing Using MATLAB, ch. 11"""
    B = np.array(B).astype(np.float64)
    M, N = B.shape
    x, y = np.meshgrid(np.arange(1,N+1), np.arange(1,M+1))

    x = x.flatten()
    y = y.flatten()
    F = B.flatten()

    def m(p,q):
        return np.sum(x**p * y**q * F)

    x_ = m(1,0) / m(0,0)
    y_ = m(0,1) / m(0,0)

    def mu(p,q):
        return np.sum((x - x_)**p * (y - y_)**q * F)

    def n(p,q): # eta sorta looks like n
        gamma = (p + q) / 2. + 1.
        return mu(p,q) / mu(0,0)**gamma

    # assign some variables so the eqns aren't impossible to read
    n20, n02 = n(2,0), n(0,2)
    n11 = n(1,1)
    n30, n03 = n(3,0), n(0,3)
    n12, n21 = n(1,2), n(2,1)
    
    phi1 = n20 + n02
    phi2 = (n20 - n02)**2 + 4 * n11**2
    phi3 = (n30 - 3 * n12)**2 + (3 * n21 - n03)**2
    phi4 = (n30 + n12)**2 + (n21 + n03)**2
    phi5 = (n30 - 3 * n12) * (n30 + n12) * \
        ( (n30 + n12)**2 - 3 * (n21 + n03)**2 ) + \
        (3 * n21 - n03) * (n21 + n03) * \
        ( 3 * (n30 + n12)**2 - (n21 + n03)**2 )
    phi6 = (n20 - n02) * \
        ( (n30 + n12)**2 - (n21 + n03)**2 ) + \
        4 * n11 * (n30 + n12) * (n21 + n03)
    phi7 = (3 * n21 - n03) * (n30 + n12) * \
        ( (n30 + n12)**2 - 3 * (n21 + n03)**2 ) + \
        (3 * n12 - n30) * (n21 + n03) * \
        ( 3 * (n30 + n12)**2 - (n21 + n03)**2 )

    return phi1, phi2, phi3, phi4, phi5, phi6, phi7

def convex_hull(perimeter_points):
    P = np.vstack(perimeter_points).T
    hull = ConvexHull(P)
    return P[hull.vertices]

def convex_hull_perimeter(hull):
    ab = hull - np.roll(hull,1,axis=0)
    ab2 = np.power(ab,2)
    D = np.sqrt(np.sum(ab2,axis=1))
    return np.sum(D)

def convex_hull_image(hull,shape):
    """this can also be computed using
    skimage.measure.regionprops"""
    chi = np.zeros(shape,dtype=np.bool)
    # points in the convex hull
    y, x = polygon(hull[:,0], hull[:,1])
    chi[y,x] = 1
    # points on the convex hull
    for row in np.hstack((hull, np.roll(hull,1,axis=0))):
        chi[line(*row)]=1
    return chi
