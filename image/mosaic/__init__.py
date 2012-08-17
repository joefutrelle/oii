#!/usr/bin/python
# create a mosaic image 
from PIL import Image
from oii.image.mosaic.binpacking import JimScottRectanglePacker

X=0
Y=1

"""Create a mosaic of images"""

class Tile(object):
    """Tile associates an image (or arbitrary payload) with a (w,h) "size" property
    and an (x,y) "position" property """
    def __init__(self,image,(w,h),position=None):
        self.image = image
        self.size = (w,h)
        self.position = position

def layout(tiles, (width, height)):
    """Fit tiles into a rectangle using a bin packing algorithm. Returns Tiles
    describing the layout.
    
    Parameters:
    tile - iterable of things with a "size" = (w,h) property.
    If you need some construct them with Tile, but you can use PIL images without
    wrapping them in Tile.
    (width, height) - the pixel dimensions of the desired mosaic"""
    packer = JimScottRectanglePacker(width, height)
    for tile in tiles:
        try: # is the tile carrying an "image" payload?
            image = tile.image # use it
        except KeyError:
            image = tile # otherwise use the tile itself
        (w,h) = tile.size
        p = packer.TryPack(w, h) # attempt to fit
        if p is not None:
            yield Tile(image, (w,h), (p.x, p.y))
    
def composite(layout, size=None, mode='RGB', bgcolor=0):
    """Construct a composite image from a layout
    
    Parameters:
    layout - the output of the layout function
    size - the (w,h) of the desired composite, or None to shrink to fit
    mode - the PIL image mode (e.g, 'L') - defaults to RGB
    bgcolor - background color fill"""
    if(size == None): # no size specified?
        # compute maximum extent of tiles
        w = max([tile.position[X] + tile.size[X] for tile in layout])
        h = max([tile.position[Y] + tile.size[Y] for tile in layout])
    else:
        (w, h) = size
    # create an image for the whole mosaic
    mosaic = Image.new(mode, (w,h))
    mosaic.paste(bgcolor,(0,0,w,h)) # fill it with a background color
    for tile in layout: # composite each tile in its right place
        mosaic.paste(tile.image, tile.position)
    return mosaic
