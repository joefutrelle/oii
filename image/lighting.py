from color import gray_world
from PIL import Image, ImageFilter, ImageChops, ImageEnhance

def estimate_lightfield(img):
    """Estimate background given an unevenly-lit lightfield image.
    1. Downscale image (for performance)
    2. Recursively compute median filter assuming foreground objects are relatively small
    3. Upscale and smooth"""
    # FIXME hardcoded params probably tuned for 5-8MP images with features of a certain size
    (w,h) = img.size;
    bg = img.resize((100,100), Image.BICUBIC)
    for i in range(5): # recursive median tends to delete objects
        bg = bg.filter(ImageFilter.MedianFilter(21));
    bg = bg.resize((w,h))
    return bg

def lightfield_correct(img,lightfield=None):
    """Subtract a lightfield produced by estimate_lightfield from an image.
    Tweaks to adjust brightness, contrast and color saturation of lightfield make the subtraction
    produce an image with reasonable brightness and contrast."""
    if lightfield is None:
        lightfield = estimate_lightfield(img)
    # FIXME hardcoded params probably tuned to certain images
    gray = ImageEnhance.Color(lightfield).enhance(0.25)
    hicontrast = ImageEnhance.Contrast(gray).enhance(2.25)
    darkened = ImageEnhance.Brightness(hicontrast).enhance(0.5)
    return ImageEnhance.Brightness(ImageChops.subtract(img, darkened)).enhance(1.5)
