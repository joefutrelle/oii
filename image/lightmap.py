import numpy as np

from skimage import img_as_float, img_as_ubyte
from skimage.io import imread, imsave
from scipy.ndimage.filters import uniform_filter, gaussian_filter

from oii.image.color import gray_value, gray_world

def smooth_cfa(cfa,footprint=8,stereo=False):
    """
    Smooth a RAW (bayer-patterned) image with a uniform filter.

    Parameters
    ----------
    cfa : ndarray
        bayer-patterned image
    footprint : int
        size of uniform filter kernel (must be multiple of 2)
    stereo : boolean
        whether image is a side-by-side stereo image, in which
        case smoothing will be performed independently on each side

    Returns
    -------
    smoothed image : ndarray
    """
    (h,w) = cfa.shape
    if footprint > 0:
        smoothed = np.zeros_like(cfa)
        if stereo:
            xs,fw = [0,w/2], w/2
        else:
            xs,fw = [0], w
        for x in xs:
            for dy in [0,1]:
                for dx in [0,1]:
                    smoothed[dy::2,x+dx:x+dx+fw:2] = uniform_filter(cfa[dy::2,x+dx:x+dx+fw:2],size=footprint/2,mode='nearest')
        return smoothed
    else:
        return cfa

def smooth_color(image,footprint=8,stereo=False):
    """
    Smooth a multi-channel image with a uniform filter. Applies same filter to all channels.

    Parameters
    ----------
    image : ndarray
        color image
    footprint : int
        size of uniform filter kernel
    stereo : boolean
        whether image is a side-by-side stereo image, in which
        case smoothing will be performed independently on each side

    Returns
    -------
    smoothed image : ndarray
    """
    (h,w,nc) = image.shape
    if footprint > 0:
        smoothed = np.zeros_like(image)
        if stereo:
            xs,fw = [0,w/2], w/2
        else:
            xs,fw = [0], w
        for x in xs:
            for c in range(nc):
                smoothed[:,x:fw,c] = uniform_filter(image[:,x:fw,c],size=footprint,mode='nearest')
        return smoothed
    else:
        return image

def accumulate(image,sum_image=None,count=0):
    """
    Accumulate a sum image.

    Parameters
    ----------
    sum_image : ndarray
        existing sum image (None if first iteration)
    count : int
        existing image count (0 if first iteration

    Returns
    -------
    sum_image : ndarray
        accumulated sum image so far (pass to next iteration)
    count : int
        number of images summed so far (pass to next iteration)
    """
    if sum_image is None:
        return (image, 1)
    else:
        sum_image += image
        return (sum_image, count+1)

class LearnLightmap(object):
    """
    Compute average of images.

    Parameters
    ----------
    stereo : boolean
        Whether images are side-by-side stereo pairs
    raw : boolean
        Whether images are RAW (Bayer-patterned). If not they are assumed to be multichannel
        and the same smoothing is applied to all channels. Note that for RAW images it does not
        matter which Bayer pattern is in use as each CFA element is averaged independently.
    """
    def __init__(self,stereo=False,raw=False):
        self.sum_image = None
        self.count = 0
        self.stereo = stereo
        self.raw = raw
    def add_image(self,image):
        """
        Add an image to the set that is being averaged.

        Parameters
        ----------
        image : ndarray
            Image data in an array
        """
        (self.sum_image, self.count) = accumulate(image,self.sum_image,self.count)
    def average_image(self,smooth=0):
        """
        Return the average of all the images
        
        Parameters
        ----------
        smooth : int
            Size of smoothing kernel (default 0, no smoothing)

        Returns
        -------
        averaged image : ndarray
            Averaged image, with optional smoothing
        """
        avg_image = self.sum_image / self.count
        if self.raw:
            avg_image = smooth_cfa(avg_image,stereo=self.stereo,footprint=smooth)
        else:
            avg_image = smooth_color(avg_image,stereo=self.stereo,footprint=smooth)
        return avg_image

class CorrectRaw(object):
    """
    Given a lightmap computed by LearnLightmap(raw=True), correct new images.
    """
    def __init__(self,cfa_lightmap):
        """
        Parameters
        ------
        cfa_lightmap : ndarray
            Bayer-patterned lightmap returned by average_image in LearnLightmap.
        """
        self.lightmap = cfa_lightmap
        self.avg_lightmap_00 = np.average(self.lightmap[::2,::2])
        self.avg_lightmap_01 = np.average(self.lightmap[::2,1::2])
        self.avg_lightmap_10 = np.average(self.lightmap[1::2,::2])
        self.avg_lightmap_11 = np.average(self.lightmap[1::2,1::2])
    def correct_image(self,image):
        """
        Correct an image with the lightmap.

        Parameters
        ----------
        image : ndarray
            Bayer-patterned image to correct. Should be floating-point

        Returns
        -------
        corrected image : ndarray
            Bayer-patterend corrected image.
        """
        new_cfa = (image - self.lightmap)
        new_cfa[::2,::2] += self.avg_lightmap_00
        new_cfa[::2,1::2] += self.avg_lightmap_01
        new_cfa[1::2,::2] += self.avg_lightmap_10
        new_cfa[1::2,1::2] += self.avg_lightmap_11
        return (new_cfa - np.min(new_cfa)).clip(0.,1.)

class CorrectRgb(object):
    """
    Given a lightmap computed by LearnLightmap(raw=False), correct new images.
    """
    def __init__(self,rgb_lightmap,color_balance=True,brightness=0.0):
        """
        Parameters
        ----------
        rgb_lightmap : ndarray
            RGB lightmap returned from average_image in LearnLightmap
        color_balance : boolean
            Whether to apply gray world color balancing to corrected images
        brightness : float
            How much to scale brightness. Default of 0.0 means to adadptively brighten
            based on average intensity. 1.0 means not to brighten.
        """
        self.lightmap = rgb_lightmap
        self.avg_lightmap = np.dstack([np.average(self.lightmap[:,:,c]) for c in range(3)])
        self.color_balance = color_balance
        self.brightness = brightness
    def correct_image(self,image):
        """
        Correct an RGB image.

        Parameters
        ----------
        image : ndarray
            3-channel color (RGB) image

        Returns
        -------
        corrected image : ndarray
            corrected image (corrected for illumination and/or color balance and/or brightness
        """
        new_rgb = (image - self.lightmap)
        new_rgb += self.avg_lightmap
        if self.color_balance:
            # here we balance to the local image rather than against the lightmap's gray value
            new_rgb = gray_world(new_rgb)
        if self.brightness == 0: # adaptive
            avg = np.average(new_rgb - np.min(new_rgb))
            factor = 0.5 / avg
        else:
            factor = self.brightness
        return ((new_rgb - np.min(new_rgb)) * factor).clip(0.,1.)

def average_image(infiles):
    learn = LearnLightmap()
    for image_path in infiles:
        learn.add_image(img_as_float(imread(image_path,plugin='freeimage')))
    return learn.average_image()

def learn_cfa(infiles,outfile,stereo=False,smooth=8):
    """Learn the average illumination for a set of RAW images.
    params:
    infiles - input files
    outfile - output file
    stereo - whether the files are L/R images or single images
    smooth - size of kernel for smoothing (0 for none)"""
    avg_image = smooth_cfa(average_image(infiles),stereo=stereo,footprint=smooth)
    imsave(outfile,avg_image)

def learn_rgb(infiles,outfile,stereo=False,smooth=4):
    """Learn the average illumiunation for a set of RGB images.
    params:
    infiles - input files
    outfile - output file
    stereo - whether the files are L/R images or single images
    smooth - size of kernel for smoothing (0 for none)"""
    avg_image = smooth_rgb(average_image(infiles),stereo=stereo,footprint=smooth)
    imsave(outfile,avg_image)
