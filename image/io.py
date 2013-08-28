import re

from skimage import img_as_float
from skimage.io import imread, imsave

"""Image I/O utilities"""

def imread_float(infile):
    """
    Read an image as a floating-point image.
    Additionally, if the input file is a TIFF, use the freeimage plugin,
    to allow for reading 16-bit TIFFs.

    Parameters
    ----------
    infile : str
        the file containing the image

    Returns
    img : ndarray of float
        the image
    """
    if re.match(r'.*\.tiff?$',infile):
        img = imread(infile,plugin='freeimage')
    else:
        img = imread(infile)
    return img_as_float(img)

def imsave_clip(outfile,img):
    """
    Save an image and clip it to 0-1.
    This really only makes sense for floating-point images
    """
    img = img_as_float(img).clip(0.,1.)
    imsave(outfile,img)
    
