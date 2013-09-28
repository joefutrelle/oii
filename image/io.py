import re

from skimage import img_as_float
from skimage import io

from oii.iopipes import UrlSource, StagedInputFile

"""Image I/O utilities"""

def imread(infile):
    def _readfile(fin):
        if re.match(r'.*\.tiff?$',fin):
            return io.imread(fin,plugin='freeimage')
        else:
            return io.imread(fin)
    if re.match(r'^https?:.*',infile):
        with StagedInputFile(UrlSource(infile)) as fin:
            img = _readfile(fin)
    else:
        img = _readfile(infile)
    return img

def imread_float(infile):
    """
    Read an image as a floating-point image.
    Additionally, if the input file is a TIFF, use the freeimage plugin,
    to allow for reading 16-bit TIFFs.

    Parameters
    ----------
    infile : str
        the file or URL containing the image

    Returns
    img : ndarray of float
        the image
    """
    return img_as_float(imread(infile))

def imsave_clip(outfile,img):
    """
    Save an image and clip it to 0-1.
    This really only makes sense for floating-point images
    """
    img = img_as_float(img).clip(0.,1.)
    io.imsave(outfile,img)
    
