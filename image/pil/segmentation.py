from color import gray_world
from lighting import estimate_lightfield
from PIL import Image, ImageFilter, ImageChops, ImageEnhance

def mask_bg(img,lightfield=None,threshold=15):
    """Crude segmentation based on difference from estimated lightfield"""
    # FIXME hardcoded params
    if lightfield is None:
        lightfield = estimate_lightfield(img)
    mask = ImageChops.difference(img, lightfield).convert('L')
    mask = ImageEnhance.Contrast(mask).enhance(2).point(lambda v: 255 if v > threshold else 0).filter(ImageFilter.MedianFilter(7))
    return mask

def bcd(img):
    """Compute a segment mask"""
    # FIXME hardcoded to tune for specific cases, need to parameterize
    # compute mask
    mask = mask_bg(img)
    # color balance
    gw = gray_world(img)
    # enhance contrast
    gw = ImageEnhance.Brightness(gw).enhance(1.75)
    gw = ImageEnhance.Contrast(gw).enhance(1.1)
    # composite on white
    return Image.composite(Image.new('L', img.size, 255), gw, ImageChops.invert(mask))





