import numpy as np
from math import ceil, log
from numpy.random import random_sample
from scipy.ndimage.interpolation import zoom

# 2d 1/f noise in the range 0-1
def scaling_noise(shape):
    (h,w) = shape
    out = np.zeros(shape,np.float)
    p = ceil(log(max(shape),2))
    for scale in np.power(2,np.arange(1,p)):
        noise = random_sample((scale,scale)) - 0.5
        out += (zoom(noise,(2**p)/scale) / scale)[:h,:w]
    out += 0.5
    return out
