import sys

import numpy as np
from numpy.random import RandomState
from skimage import img_as_float
from skimage.io import imread, imsave
from skimage.color import rgb2gray
from skimage.transform import resize
from skimage.feature import match_template
from scipy.ndimage.filters import uniform_filter, gaussian_filter
from scipy.ndimage.measurements import maximum_position

from oii import resolver
from oii.image.color import gray_world
from oii.image.demosaic import demosaic
from oii.habcam.lightfield.batch import list_images, as_tiff

#RESOLVER='/home/jfutrelle/honig/oii/habcam/image_resolver.xml'

#resolvers = resolver.parse_stream(RESOLVER)
#pid2tiff = resolvers['image']

#IMAGE='201203.20120623.121507545.97672'
#IMAGE='201203.20120623.114028643.85250'

#hit = pid2tiff.resolve(pid=as_tiff(IMAGE))

#cfa_LR = img_as_float(imread(hit.value,plugin='freeimage'))

def chop_stereo(img):
    (_,w) = img.shape
    return img[:,:w/2], img[:,w/2:]

def lightfield(rgb):
    (_,w,_) = rgb.shape
    # color balance
    cb = gray_world(rgb).clip(0.,1.)
    # estimate background
    rf = uniform_filter(cb,w/3)
    # subtract it from image
    sb = cb - rf
    # rescale
    sb = (sb - sb.min()) / sb.ptp()
    # gamma, brightness
    sb = np.power(sb,4./3.) * 2
    # apply unsharp mask
    s = 3
    um = gaussian_filter(sb,10)
    sharp = ((s / (s - 1)) * (sb - um / s)).clip(0.,1.)
    return sharp

def lightfield_stereo(rgb_LR):
    (_,w,_) = rgb_LR.shape
    flat_LR = np.zeros_like(rgb_LR)
    # correct each side independently
    flat_LR[:,:w/2,:] = lightfield(rgb_LR[:,:w/2,:])
    flat_LR[:,w/2:,:] = lightfield(rgb_LR[:,w/2:,:])
    return flat_LR

def align(y_LR,size=64,n=12):
    (h,w) = y_LR.shape
    # split image
    y_L = y_LR[:,:w/2]
    y_R = y_LR[:,w/2:]
    (h,w) = y_L.shape
    s = size / 2
    # now find n offsets
    R = np.zeros((n,2))
    rand = RandomState(0)
    for i in range(n): # to find each offset
        # at a random locations in y_L
        y = rand.randint(h/4,h*3/4)
        x = rand.randint(w/4,w*3/4)
        it = y_L[y:y+s,x:x+s] # take an s x s chunk there
        tm = match_template(y_R,it) # match it against y_R
        ry, rx = maximum_position(tm) # max value is location
        R[i,:] = ((y-ry), (x-rx)) # accumulatea
    # take the median
    dy, dx = np.median(R,axis=0).astype(int)
    return dy, dx

def align_converge(y_LR,size=64):
    """iterate until offsets converge"""
    (h,w) = y_LR.shape
    # split image
    y_L = y_LR[:,:w/2]
    y_R = y_LR[:,w/2:]
    (h,w) = y_L.shape
    s = size / 2
    # now find n offsets
    rand = RandomState(0)
    prev_dx, prev_dy = 0, 0
    series = []
    while True:
        # at a random locations in y_L
        y = rand.randint(h/4,h*3/4)
        x = rand.randint(w/4,w*3/4)
        it = y_L[y:y+s,x:x+s] # take an s x s chunk there
        tm = match_template(y_R,it) # match it against y_R
        ry, rx = maximum_position(tm) # max value is location
        series += [((y-ry), (x-rx))] # accumulatea
        n = len(series)
        if n % 6 == 0:
            # take the median
            dy, dx = np.median(np.asarray(series),axis=0).astype(int)
            if n > 100 or (abs(dy-prev_dy) == 0 and abs(dx-prev_dx) == 0):
                return dy, dx
            prev_dy, prev_dx = dy, dx

def redcyan(y_LR,gamma=1.2,brightness=1.2,dx=None,dy=None,downscale=1,**kw):
    if dx is None or dy is None:
        y_LR_ds = y_LR[::downscale,::downscale]
        dy, dx = align(y_LR_ds,**kw)
        dy *= downscale
        dx *= downscale
    (h,w) = y_LR.shape
    w /= 2
    # gamma-correct and brighten while splitting stereo
    y_L = (np.power(y_LR[:,:w],gamma) * brightness).clip(0.,1.)
    y_R = (np.power(y_LR[:,w:],gamma) * brightness).clip(0.,1.)
    # composite red/cyan image
    out = np.zeros((h,w,3))
    out[:,:,0] = y_L # left on red channel
    # on gb channels, offset right
    out[dy:,dx:,1] = y_R[:-dy,:-dx]
    out[dy:,dx:,2] = y_R[:-dy,:-dx]
    # output overlapping regions
    return out[dy:,dx:,:]

