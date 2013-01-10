import sys

import numpy as np
from skimage import img_as_float
from skimage.io import imread, imsave
from skimage.transform import resize
from scipy.ndimage.filters import uniform_filter, gaussian_filter

from oii import resolver
from oii.image.color import gray_world
from oii.image.demosaic import demosaic
from oii.habcam.lightfield.batch import list_images, as_tiff

RESOLVER='/home/jfutrelle/honig/oii/habcam/image_resolver.xml'

resolvers = resolver.parse_stream(RESOLVER)
pid2tiff = resolvers['image']

#IMAGE='201203.20120623.121507545.97672'
IMAGE='201203.20120623.114028643.85250'

hit = pid2tiff.resolve(pid=as_tiff(IMAGE))

img = img_as_float(imread(hit.value,plugin='freeimage'))
rgb = demosaic(img,'rggb')
(h,w,_) = rgb.shape
rgb = rgb[:,:w/2,:]
(h,w,_) = rgb.shape
aspect = 1. * w / h
H=720
rgb = resize(rgb,(H, int(H * aspect)))
# color balance
cb = gray_world(rgb).clip(0.,1.)
# estimate background
rf = uniform_filter(cb,150)
# subtract it from image
sb = cb - rf
# rescale
sb = (sb - sb.min()) / sb.ptp()
# increase contrast
a = 1.3
sb = (((sb - 0.5) * a) + 0.5).clip(0.,1.)
# apply unsharp mask
s = 3
um = gaussian_filter(sb,10)
sharp = ((s / (s - 1)) * (sb - um / s)).clip(0.,1.)
# brighten
sharp = (sharp * 1.5).clip(0.,1.)
