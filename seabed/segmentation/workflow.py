from PIL import Image
from skimage.io import imread, imsave
from celery import Celery

from oii.seabed.segmentation.segment import segment

celery = Celery('oii.seabed.segmentation.workflow')

@celery.task
def segment_coral(rgb_in, y_out):
    """rgb_in should be the path to an input image. Must be 8 bit.
    y_out is a path to the result blob tag image"""
    img_in = Image.open(rgb_in)
    img_out = segment(img_in)
    imsave(y_out, img_out)
