#!/usr/bin/python
# create a mosaic image containing multiple ROI's from the given bin
from PIL import Image
from oii.image.mosaic.binpacking import JimScottRectanglePacker

"""Create a mosaic of images"""

def layout(images, (width, height)):
    """Fit images into a rectangle using a bin packing algorithm. Returns structures
    describing the layout.
    
    Parameters:
    images - the images (anything with a 'size'=(w,h) property), in the desired packing order
    (width, height) - the pixel dimensions of the desired mosaic"""
    packer = JimScottRectanglePacker(width, height)
    for image in images:
        (w,h) = image.size
        p = packer.TryPack(w, h) # attempt to fit
        if p is not None:
            yield {
                'image': image,
                'x': p.x,
                'y': p.y,
                'w': w,
                'h': h
            }
    
def composite(layout, size=None, mode='L', bgcolor=0):
    """Construct a composite image from a layout
    
    Parameters:
    layout - the output of the layout function
    size - the (w,h) of the desired composite, or None to shrink to fit
    mode - the PIL image mode (e.g, 'L')
    bgcolor - background color fill"""
    if(size == None):
        width = max([tile['x'] + tile['w'] for tile in layout])
        height = max([tile['y'] + tile['h'] for tile in layout])
    else:
        (width, height) = size
    mosaic = Image.new(mode, (width,height))
    mosaic.paste(bgcolor,(0,0,width,height))
    for entry in layout:
        mosaic.paste(entry['image'], (entry['x'], entry['y']))
    return mosaic
           
def thumbnail(image, wh):
    image.thumbnail(wh, Image.ANTIALIAS)
    return image