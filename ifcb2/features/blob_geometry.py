import numpy as np

from numpy.linalg import eig

from scipy.spatial import ConvexHull
from skimage.draw import polygon

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
    Digital Image Processing in MATLAB, ch. 11"""
    B = np.array(B).astype(np.bool)
    M, N = B.shape
    x, y = np.meshgrid(np.arange(1,N+1), np.arange(1,M+1))

    x = x.flatten()
    y = y.flatten()
    F = B.flatten().astype(float)

    def m(p,q):
        return np.sum(x**p * y**q * F)

    x_ = m(1,0) / m(0,0)
    y_ = m(0,1) / m(0,0)

    def mu(p,q):
        return np.sum((x - x_)**p * (y - y_)**q * F)

    @np.vectorize
    def eta(p,q):
        gamma = (p + q) / 2. + 1.
        return mu(p,q) / mu(0,0)**gamma

    q, p = np.meshgrid(np.arange(4),np.arange(4))
    e = eta(p,q)

    phi1 = e[2,0] + e[0,2]
    phi2 = (e[2,0] - e[0,2])**2 + 4 * e[1,1]**2
    phi3 = (e[3,0] - 3 * e[1,2])**2 + (3 * e[2,1] - e[0,3])**2
    phi4 = (e[3,0] + e[1,2])**2 + (e[2,1] + e[0,3])**2
    phi5 = (e[3,0] - 3 * e[1,2]) * (e[3,0] + e[1,2]) * \
        ( (e[3,0] + e[1,2])**2 - 3 * (e[2,1] + e[0,3])**2 ) + \
        (3 * e[2,1] - e[0,3]) * (e[2,1] + e[0,3]) * \
        ( 3 * (e[3,0] + e[1,2])**2 - (e[2,1] + e[0,3])**2 )
    phi6 = (e[2,0] - e[0,2]) * \
        ( (e[3,0] + e[1,2])**2 - (e[2,1] + e[0,3])**2 ) + \
        4 * e[1,1] * (e[3,0] + e[1,2]) * (e[2,1] + e[0,3])
    phi7 = (3 * e[2,1] - e[0,3]) * (e[3,0] + e[1,2]) * \
        ( (e[3,0] + e[1,2])**2 - 3 * (e[2,1] + e[0,3])**2 ) + \
        (3 * e[1,2] - e[3,0]) * (e[2,1] + e[0,3]) * \
        ( 3 * (e[3,0] + e[1,2])**2 - (e[2,1] + e[0,3])**2 )

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
    chi = np.zeros(shape,dtype=np.bool)
    y, x = polygon(hull[:,0], hull[:,1])
    chi[y,x] = 1
    return chi
