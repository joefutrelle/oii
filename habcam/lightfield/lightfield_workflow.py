from celery import Celery

from skimage.io import imread, imsave

from oii.iopipes import StagedInputFile, UrlSource
from oii.habcam.lightfield import altitude

MODULE = 'oii.habcam.lightfield'

celery = Celery(MODULE)

def read_image(url_or_filename,plugin='freeimage'):
    try:
        return imread(url_or_filename,plugin=plugin)
    except:
        with StagedInputFile(UrlSource(url_or_filename)) as imfile:
            return imread(imfile,plugin=plugin)
            
@celery.task(name='oii.habcam.stereo2altitude')
def stereo2altitude(cfa_LR,config={}):
    cfa_LR = read_image(cfa_LR,plugin='freeimage')
    (x,y,m) = altitude.stereo2altitude(cfa_LR)
    print 'altitude = (%d,%d,%.2f)' % (x,y,m) # FIXME debug
    return (x,y,m)

@celery.task(name='oii.habcam.stereo2mono')
def stereo2mono(tif_file,outfile,side='L'):
    """crop a single-channel image into L or R side
    tif_file: filename or URL of the single-channel image
    outfile: where to put the L or R side
    side: whether to produce the L or R side (use 'L' or 'R')
    returns: ((height,width),output file name)"""
    cfa_LR = read_image(tif_file,plugin='freeimage')
    (h,w) = cfa_LR.shape
    if side == 'L':
        imsave(outfile,cfa_LR[:,:w/2],plugin='freeimage')
    else:
        imsave(outfile,cfa_LR[:,w/2:],plugin='freeimage')
    print 'split %s' % tif_file
    return ((h,w),outfile)
        
