import numpy as np

from skimage.morphology import convex_hull_images

def areas(blobs):
    return [np.sum(np.array(B).astype(np.bool)) for B in blobs]
    
def extents(blobs,blob_areas=None):
    if blob_areas is None:
        blob_areas = areas(blobs)
    return [(float(a) / (b.shape[0] * b.shape[1])) for a,b in zip(areas,blobs)]
    
def convex_areas(blobs,convex_hull_images=None):
    if convex_hull_images is None:
        convex_hull_images = [convex_hull_image(B) for B in blobs]
    return [np.sum(ch.astype(np.bool)) for ch in convex_hull_images]

def solidities(areas, convex_areas):
    return [float(a)/ca for a,ca in zip(areas, convex_areas)]

def ellipse_properties(blob):
    """returns major axis length, minor axis length, eccentricity,
    and orientation"""
    P = np.vstack(np.where(blob))
    S = np.cov(P)
    x, y = np.diag(S)
    xy = S[1,0] # S[0,1] would work too
    
    c = np.sqrt((x-y)**2 - 4*xy**2)

    maj_axis = 2 * np.sqrt(2) * np.sqrt(x + y + c)
    min_axis = 2 * np.sqrt(2) * np.sqrt(x + y - c)
    
    ecc = np.sqrt(1-(min_axis/maj_axis)**2)
    
    if y > x:
        n = y - x + np.sqrt((y-x)**2 + 4*xy**2)
        d = 2 * xy
    else:
        n = 2 * xy
        d = x - y + np.sqrt((x-y)**2 + 4*xy**2)
    if n==0 and d==0:
        orientation = 0
    else:
        orientation = (180/np.pi) * np.arctan(n/d) - 90
        
    return maj_axis, min_axis, ecc, orientation

def invmoments(image):
    """compute invariant moments. see
    Digital Image Processing in MATLAB, ch. 11"""
    M, N = image.shape
    x, y = np.meshgrid(np.arange(1,N+1), np.arange(1,M+1))

    x = x.flatten()
    y = y.flatten()
    F = image.flatten().astype(float)

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

