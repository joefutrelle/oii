import numpy as np

from numpy.fft import fft2, fftshift

from scipy.ndimage.interpolation import zoom

from skimage.draw import circle, polygon

from oii.utils import memoize

# original MATLAB implementation: Kaccie Li, 2005
# Python port: Joe Futrelle, 2016

_DIM=301

_eps = np.finfo(float).eps

@memoize
def ring_mask(i,dim=_DIM):
    # ring masks are a series of 50 concentric rings, each dim/100
    # pixels thick, around the center of the dim x dim array
    s = dim/100.
    rmin = (i * s) + _eps
    rmax = (i+1) * s
    c = (dim//2)+1
    mask = np.zeros((dim,dim),dtype=np.bool)
    mask[circle(c,c,rmax)]=True
    mask[circle(c,c,rmin)]=False
    return mask
    
@memoize
def wedge_mask(i,dim=_DIM):
    # wedge masks are a series of 48 triangles between the center of
    # the dim x dim array and two adjacent vertices of a radius dim/100
    # semicircle divided into 48 arc segments. the semicircle is the
    # bottom half of a dim x dim array.
    mask = np.zeros((dim,dim),dtype=np.bool)
    c = (dim//2)
    def theta(i):
        return -1. * i * (np.pi / 48.) + (np.pi / 2.)
    def vertex(i):
        return c + np.cos(theta(i)) * (dim//2), c + np.sin(theta(i)) * (dim//2)
    v1y, v1x = vertex(i)
    v2y, v2x = vertex(i+1)
    wy, wx = np.array([c, v1y, v2y]), np.array([c, v1x, v2x])
    mask[polygon(wy,wx)]=True
    mask[c,c:]=0 # exclude the right side of the central horizontal
    mask[:,c]=0 # exclude the central vertical
    return mask
    
@memoize
def filter_masks(dim=_DIM):
    # FIXME simplify using skimage.draw.circle
    # the mask and filter generated here are the center of the fft
    # where most of the energy is found
    df = 1./((dim-1.)*6.45)
    f = np.arange(-0.5/6.45, 0.5*1/6.45, df)
    I,J = np.meshgrid(f,f)
    d = I**2 + J**2
    mask = np.zeros((dim,dim),dtype=np.bool)
    mask[d < (15*df)**2]=1
    filt=np.invert(mask)
    return mask, filt
    
def ring_wedge(image,dim=_DIM):
    # perform fft and scale its intensities to dim x dim
    amp_trans = fftshift(fft2(image))
    int_trans = np.real(amp_trans * np.conj(amp_trans))
    z = (1.*dim/image.shape[0], 1.*dim/image.shape[1])
    int_trans = zoom(int_trans,z,order=1) # bilinear
    # now compute stats of filtered intensities
    mask, filt = filter_masks(dim)
    filter_img = mask * int_trans
    # intensities inside central area
    inner_int = np.sum(filter_img)
    # total intensity
    total_int = np.sum(int_trans)
    # ratio between central intensity and total intensity
    pwr_ratio = inner_int / total_int
    # now mask the intensities for wedge and ring calculations
    wedge_int_trans = int_trans * filt # wedges exclude center
    # only use the bottom half
    half = np.vstack((np.zeros(((dim//2)+1,dim)), np.ones((dim//2,dim)))).astype(np.bool)
    wedge_half = wedge_int_trans * half
    ring_half = int_trans * half
    # now compute unscaled wedge and ring vectors for all wedges and rings
    # these represent the total power found in each ring / wedge
    wedge_vector = np.array([np.sum(wedge_mask(i) * wedge_half) for i in range(48)])
    ring_vector = np.array([np.sum(ring_mask(i) * ring_half) for i in range(50)])
    # compute power integral over wedge vectors and scale vectors by it
    pwr_integral = np.sum(wedge_vector)
    wedges = wedge_vector / pwr_integral
    rings = ring_vector / pwr_integral
    # return all features
    return pwr_integral, pwr_ratio, wedges, rings
