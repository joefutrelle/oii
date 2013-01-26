import logging
from celery import Celery, group

import numpy as np

from skimage import img_as_float
from skimage import io
from skimage import color

from oii.image.demosaic import demosaic as debayer
from oii.habcam.lightfield import quick

class CONFIG:
    CELERY_AMQP_TASK_RESULT_EXPIRES=30
#memcached://127.0.0.1:11211/')
celery = Celery('oii.habcam.workflow', broker='amqp://guest@localhost//', backend='amqp')
celery.config_from_object(CONFIG)

@celery.task
def imread(fn):
    logging.info('reading %s' % fn)
    img = img_as_float(io.imread(fn,plugin='freeimage'))
    logging.info('read %s' % fn)
    return img

@celery.task
def demosaic(img,pattern):
    img = debayer(img,pattern)
    return img

@celery.task
def imsave(img,fn):
    io.imsave(fn,img)
    return fn

@celery.task
def split_L(y_LR):
    (_,w) = y_LR.shape
    return y_LR[:,:w/2]

@celery.task
def split_R(y_LR):
    (_,w) = y_LR.shape
    return y_LR[:,w/2:]

@celery.task
def rgb2gray(rgb):
    return color.rgb2gray(rgb)

@celery.task
def align(y_LR,size=64,n=6):
    return quick.align(y_LR,size,n)

@celery.task
def power(img,gamma=1.0):
    return np.power(img,gamma)

@celery.task
def multiply(img,brightness=1.0):
    return (img * brightness).clip(0.,1.)

@celery.task
def merge((red_L,cyan_R,(dy,dx))):
    (h,w) = red_L.shape
    out = np.zeros((h,w,3))
    out[:,:,0] = red_L
    out[dy:,dx:,1] = cyan_R[:-dy,:-dx]
    out[dy:,dx:,2] = cyan_R[:-dy,:-dx]
    return out[dy:,dx:,:]

def redcyan(cfa_LR,fout,pattern='rggb',gamma=1.2,brightness=1.2):
    """Return a workflow that can be executed via the celery API"""
    yx = power.s(gamma) | multiply.s(brightness)
    red_L = split_L.s() | yx
    cyan_R = split_R.s() | yx
    y_LR = imread.s(cfa_LR) | demosaic.s(pattern) | rgb2gray.s()
    return y_LR | group(red_L, cyan_R, align.s()) | merge.s() | imsave.s(fout)

@celery.task
def quick_redcyan(cfa_LR,fout,pattern='rggb',gamma=1.2,brightness=1.2):
    y_LR = rgb2gray(demosaic(imread(cfa_LR),pattern))
    def yx(img):
        return multiply(power(img,gamma),brightness)
    red_L = yx(split_L(y_LR))
    cyan_R = yx(split_R(y_LR))
    (dy, dx) = align(y_LR)
    imsave(merge((red_L, cyan_R, (dy, dx))), fout)
    return fout

