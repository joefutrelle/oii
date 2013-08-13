import re

import numpy as np

from skimage.exposure import equalize
from skimage.feature import match_template

from oii.habcam.lightfield.quick import align_better

# configuration keys for tasks, and their defaults
BAYER_PATTERN = 'bayer_pattern'
CAMERA_SEPARATION = 'camera_separation'
FOCAL_LENGTH = 'focal_length'
H2O_ADJUSTMENT = 'h2o_adjustment' # there has got to be a better name for this
PIXEL_SEPARATION = 'pixel_separation'

CONFIG_DEFAULTS = {
    # these camera params are for the V4 camera
    BAYER_PATTERN: 'rggb', #
    CAMERA_SEPARATION: 0.235, # distance between stereo cameras in m (23.5cm)
    FOCAL_LENGTH: 0.012, # cameras' focal length (12mm)
    H2O_ADJUSTMENT: 1.25, # dimensionless
    PIXEL_SEPARATION: 0.00000645, # distance between pixels in m
}

def my(d,k):
    """returns value of key from d or if missing from CONFIG_DEFAULTS"""
    try:
        return d[k]
    except KeyError:
        return CONFIG_DEFAULTS[k]

def align(cfa_LR,config={}):
    # configure
    bayer_pattern = my(config,BAYER_PATTERN)
    # average green channels together to estimate y_LR
    # this also downscales image 2x
    if re.match('.gg.',bayer_pattern,re.I):
        g_LR = (cfa_LR[::2,1::2] + cfa_LR[1::2,::2]) / 2.
    else:
        g_LR = (cfa_LR[::2,::2] + cfa_LR[1::2,1::2]) / 2.
    # jack up contrast to exaggerate texture
    g_LR = equalize(g_LR)
    # gather metrics
    (h,w) = g_LR.shape
    h2 = h/2 # half the height (center of image)
    w2 = w/2 # half the width (split between image pair)
    w4 = w/4 # 1/4 the width (center of left image)
    w34 = w2 + w4 # 3/4 the width (center of right image)
    template_size = 32
    ts = template_size
    ts2 = template_size / 2
    out = np.zeros((h,w2)) # FIXME
    for ox in [0,ts,0-ts]:
        for i in range(h/ts):
            y = (i * ts)
            # select the center pixels of the left image
            template = g_LR[y:y+ts,(w4+ox)-ts2:(w4+ox)+ts2]
            # now match the template to the corresponding horizontal strip of the right image
            # and accumulate into an output "strips" image
            strip = g_LR[y:y+ts,w2:]
            out[y:y+ts,:] += np.roll(match_template(strip,template,pad_input=True),0-ox,axis=1)
    # sum to horizontal scanline
    scanline = np.sum(out,axis=0)
    padding = w2/8 # ignore image edges
    max_x = np.argmax(scanline[padding:-padding]) + padding
    # offset is difference from half the width of each image in the pair
    # upscaled by a factor of 2
    dx = (w4 - max_x) * 2
    return dx

def p2m(offset,config={}):
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
            
def stereo2altitude(cfa_LR,**config):
    """cfa_LR: bayer-pattern stereo pair single-channel image
    config: config with the following keys:
    - BAYER_PATTERN
    - CAMERA_SEPARATION
    - FOCAL_LENGTH
    - H2O_ADJUSTMENT
    - PIXEL_SEPARATION
    all of which have defaults.
    returns: (x offset, y offset, altitude in m)"""
    bayer_pattern = my(config,BAYER_PATTERN)
    # now perform alignment
    try:
        x = align(cfa_LR,config)
        # now do a sanity check on the alignment results
        if x <= 0: # in this case we have to either skip the image or emit a bogus value
            raise UserWarning()
        m = p2m(x,config)
        return (x,0,m)
    except:
        # emit a bogus value of 1.6m and indicate with -1,-1
        return (-1,-1,1.6) # emit bogus value
