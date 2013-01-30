import os
import logging
import shutil

import numpy as np

from skimage import img_as_float
from skimage import io
from skimage import color

from oii.utils import relocate
from oii.image.demosaic import demosaic as debayer
from oii.habcam.lightfield import quick

from celery import Celery, group

class CONFIG:
    BROKER_URL='amqp://guest@localhost//'
    CELERY_RESULT_BACKEND='amqp'
    CELERY_TASK_RESULT_EXPIRES=30
tasks = Celery('oii.habcam.workflow')
tasks.config_from_object(CONFIG)

@tasks.task
def imread(fn):
    logging.info('reading %s' % fn)
    img = img_as_float(io.imread(fn,plugin='freeimage'))
    logging.info('read %s' % fn)
    return img

@tasks.task
def demosaic(img,pattern):
    img = debayer(img,pattern)
    return img

def cfa2y(cfa,pattern='rggb'):
    return color.rgb2gray(demosaic(imread(cfa),pattern))

@tasks.task
def imsave(img,fn):
    io.imsave(fn,img)
    return fn

@tasks.task
def split_L(y_LR):
    (_,w) = y_LR.shape
    return y_LR[:,:w/2]

@tasks.task
def split_R(y_LR):
    (_,w) = y_LR.shape
    return y_LR[:,w/2:]

@tasks.task
def align(y_LR,size=64,n=6):
    return quick.align(y_LR,size,n)

def power(img,gamma=1.0):
    return np.power(img,gamma)

def multiply(img,brightness=1.0):
    return (img * brightness).clip(0.,1.)

@tasks.task
def merge((red_L,cyan_R,(dy,dx))):
    (h,w) = red_L.shape
    out = np.zeros((h,w,3))
    out[:,:,0] = red_L
    out[dy:,dx:,1] = cyan_R[:-dy,:-dx]
    out[dy:,dx:,2] = cyan_R[:-dy,:-dx]
    return out[dy:,dx:,:]

@tasks.task
def quick_redcyan(cfa_LR,fout,pattern='rggb',gamma=1.2,brightness=1.2):
    y_LR = cfa2y(cfa_LR, pattern)
    def yx(img):
        return multiply(power(img,gamma),brightness)
    red_L = yx(split_L(y_LR))
    cyan_R = yx(split_R(y_LR))
    (dy, dx) = align(y_LR)
    imsave(merge((red_L, cyan_R, (dy, dx))), fout)
    return fout

@tasks.task
def align_raw(cfa_LR,pattern='rggb',size=64,n=6):
    """compute pixel offset from correspondence.
    params:
    - pattern = bayer pattern
    - size = size of region to match
    - n = number of regions to sample"""
    y_LR = cfa2y(cfa_LR, pattern)
    (dy, dx) = align(y_LR, size=size, n=n)
    return (dy, dx)

#@tasks.task
#def stage_cfa_LR(cfa_LR, tmp_dir):
#    staged = relocate(cfa_LR, tmp_dir)
#    if not os.path.exists(staged):
#        logging.info('staging %s' % cfa_LR)
#        shutil.copy(cfa_LR, staged)
#    return staged

@tasks.task
def dummy(offset):
    print 'got %s' % str(offset)
