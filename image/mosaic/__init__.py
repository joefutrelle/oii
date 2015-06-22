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

def layout(tiles, (width, height), page=1, threshold=1.0):
    """Fit tiles into a rectangle using a bin packing algorithm. Returns Tiles
    describing the layout.
    
    Parameters:
    tile - iterable of things with a "size" = (w,h) property.
    If you need some construct them with Tile, but you can use PIL images without
    wrapping them in Tile.
    (width, height) - the pixel dimensions of the desired mosaic.
    threshold -
    Because multi-page layouts are expensive, after enough failures to pack,
    the rest of the tiles are skipped, according to a threshold expressed
    as a fraction of the tiles attempted. the default is 1.0, or no skipping.
    Lower thresholds may mean more, sparser pages, but will greatly increase
    performance."""
    while page > 0: # for each page
        # initialize a packer, and run tracking
        packer = JimScottRectanglePacker(width, height)
        (run, max_run) = (0, 0)
        for tile in tiles: # for each tile
            (w,h) = tile.size
            tile.position = packer.TryPack(w,h) # attempt to fit
            if tile.position is None: # if not
                run += 1 # track run length of misses
                if run > len(tiles) * threshold:
                    break
            else: # this tile has been positioned, reset miss run
                if run > 0 and run > max_run:
                    max_run = run
                run = 0
        if page == 1: # on the desired page?
            # return the tiles that were positioned
            tiles[:] = [tile for tile in tiles if tile.position is not None]
            return tiles
        else:
            # remove the positioned tiles and recur
            tiles[:] = [tile for tile in tiles if tile.position is None]
            page -= 1
    
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
