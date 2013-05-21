import re

from skimage.io import imread, imsave

from oii.habcam.lightfield.quick import align

# configuration keys for tasks, and their defaults
BAYER_PATTERN = 'bayer_pattern'
CAMERA_SEPARATION = 'camera_separation'
FOCAL_LENGTH = 'focal_length'
H2O_ADJUSTMENT = 'h2o_adjustment' # there has got to be a better name for this
PIXEL_SEPARATION = 'pixel_separation'

ALIGN_PATCH_SIZE = 'align_patch_size'
ALIGN_N = 'align_n'
ALIGN_DOWNSCALE = 'align_downscale'

CONFIG_DEFAULTS = {
    # these camera params are for the V4 camera
    BAYER_PATTERN: 'rggb', #
    CAMERA_SEPARATION: 0.235, # distance between stereo cameras in m (23.5cm)
    FOCAL_LENGTH: 0.012, # cameras' focal length (12mm)
    H2O_ADJUSTMENT: 1.25, # dimensionless
    PIXEL_SEPARATION: 0.00000645, # distance between pixels in m
    ALIGN_PATCH_SIZE: 128, # size of patches to compare for alignment (before downscaling)
    ALIGN_N: 6, # number of sample patches to match during alignment
    ALIGN_DOWNSCALE: 4, # how much to downscale image for alignment (must be multiple of 2)
}

def my(d,k):
    """returns value of key from d or if missing from CONFIG_DEFAULTS"""
    try:
        return d[k]
    except KeyError:
        return CONFIG_DEFAULTS[k]

def p2m(offset,config):
    """offset: pixel parallax offset
    config: config with the following keys:
    - CAMERA_SEPARATION
    - FOCAL_LENGTH
    - H2O_ADJUSTMENT
    - PIXEL_SEPARATION
    all of which have defaults.
    returns: distance to target in m"""
    camera_separation = my(config,CAMERA_SEPARATION)
    focal_length = my(config,FOCAL_LENGTH)
    h2o_adjustment = my(config,H2O_ADJUSTMENT)
    pixel_separation = my(config,PIXEL_SEPARATION)
    return (camera_separation * focal_length * h2o_adjustment) / (offset * pixel_separation)
            
def stereo2altitude(cfa_LR,config={}):
    """cfa_LR: bayer-pattern stereo pair single-channel image
    config: config with the following keys:
    - BAYER_PATTERN
    - CAMERA_SEPARATION
    - FOCAL_LENGTH
    - H2O_ADJUSTMENT
    - PIXEL_SEPARATION
    - ALIGN_PATCH_SIZE
    - ALIGN_N
    - ALIGN_DOWNSCALE
    all of which have defaults.
    returns: (x offset, y offset, altitude in m)"""
    bayer_pattern = my(config,BAYER_PATTERN)
    align_patch_size = my(config,ALIGN_PATCH_SIZE)
    align_n = my(config,ALIGN_N)
    align_downscale = my(config,ALIGN_DOWNSCALE)
    # now downscale the green channel
    if re.match('.gg.',bayer_pattern):
        (xo, yo) = (1, 0)
    else:
        (xo, yo) = (0, 0)
    y_LR = cfa_LR[xo::align_downscale,yo::align_downscale]
    # now perform alignment
    (y,x) = align(y_LR,size=align_patch_size/align_downscale,n=align_n)
    y *= align_downscale
    x *= align_downscale
    m = p2m(x,config)
    return (x,y,m)
