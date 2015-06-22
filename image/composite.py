from skimage.color import gray2rgb
from skimage import img_as_float

def overlay(fg_rgba,bg_rgb):
    """overlay an image with an alpha-channel on a background image
    params:
    ------
    fg_rgba : ndimage
        foreground image with 4th alpha channel
    bg_rgb : ndimage
        background image
    """
    fg_rgb = fg_rgba[:,:,:3]
    mask = gray2rgb(img_as_float(fg_rgba[:,:,3]))
    return (fg_rgb * mask) + (bg_rgb * (1-mask))

def bwoverlay(fg_y,bg_y,mask):
    """overlay a grayscale image on another
    params:
    ------
    fg_y : ndimage
        foreground grayscale image
    bg_y : ndimage
        background grayscale image
    mask : ndimage
        mask (max=foreground, min=background)
    """
    mask = img_as_float(mask)
    return (fg_y * mask) - (bg_y * (1-mask))
