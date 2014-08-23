import re
from StringIO import StringIO

import numpy as np
from PIL import Image

from skimage import img_as_float
from skimage import io

from oii.iopipes import UrlSource, StagedInputFile

from oii.image.pil.utils import mimetype2format

"""Image conversion utilities"""

def as_pil(array_or_image):
    try:
        return Image.fromarray(array_or_image)
    except TypeError:
        # likely a floating-point image. attempt conversion to 8-bit
        array_or_image *= 255
        array_or_image = array_or_image.astype(np.uint8) # after numpy 1.7.1, use copy=False
        return Image.fromarray(array_or_image)
    except:
        return array_or_image

def as_numpy(array_or_image):
    return np.array(array_or_image)

def as_bytes(array_or_image,mimetype='image/png'):
    """determine image format from mime type.
    currently only works for PIL-supported formats.
    default mime type is image/png"""
    buf = StringIO()
    fmt = mimetype2format(mimetype)
    im = as_pil(array_or_image).save(buf,fmt)
    return buf.getvalue()

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
    
