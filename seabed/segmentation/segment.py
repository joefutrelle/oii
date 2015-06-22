#!/usr/bin/env python
import Image
import operator
import glob
import re
import numpy as np

from scipy.ndimage.filters import generic_filter, uniform_filter, minimum_filter, maximum_filter
from scipy.ndimage import morphology

def disk_strel(radius): # For morphological operations.
  # Dimensions of (square) structuring element
  sz = 2*radius + 1
  # Return mask of points whose centers are no further away than 'radius'
  x,y = np.mgrid[:sz,:sz]
  return np.sqrt((x-radius)**2 + (y-radius)**2) <= radius

def rgb2ybr(rgb):
  """Convert uint8 (N x M x RGB) to uint8 (N x M x YCbCr) array.
  From wikipedia (sadly)."""
  # The 0.5 I'm adding is to allow floor() via cast, instead of rounding (fast)
  y  = (np.dot(rgb, [0.25678824,   0.50412941,  0.09790588]) + 16.5).clip(0,255)
  cb = (np.dot(rgb, [-0.14822353, -0.29099216,  0.43921569]) + 128.5).clip(0,255)
  cr = (np.dot(rgb, [ 0.43921569, -0.36778824, -0.07142745]) + 128.5).clip(0,255)
  return np.uint8(np.dstack((y,cb,cr)))

def ybr2rgb(ybr):
  """Convert uint8 (N x M x YCbCr) to uint8 (N x M x RGB) array.
  From wikipedia (sadly)."""
  # npote that the offsets are 0.5 off from the recommended to allow rounding.
  r = (np.dot(ybr, [ 1.16438281,   0.,          1.59602734]) - 222.421).clip(0,255)
  g = (np.dot(ybr, [ 1.16438281,  -0.39176172, -0.81296875]) + 136.076).clip(0,255)
  b = (np.dot(ybr, [ 1.16438281,   2.01723438,  0.        ]) - 276.336).clip(0,255)
  return np.uint8(np.dstack((r,g,b)))

def varfilt(a, size):
  a = np.float32(a)
  sum = uniform_filter(a, (size, size, 1))
  mean = sum
  expdev = (a - mean)**2
  sum = uniform_filter(expdev, (size, size, 1))
  return sum

def alternating_sequence_filter(data, max_radius):
  for radius in range(1, max_radius+1):
    se = disk_strel(radius)
    opened = morphology.binary_opening(data, se)
    return morphology.binary_closing(opened, se)

def fill_shadows(classmap, is_shadow):
  old_classmap = classmap.copy()
  border_pixels = is_shadow & (maximum_filter(classmap, 3) != minimum_filter(classmap, 3))
  xii,yii = border_pixels.nonzero()
  for yi, xi in zip(xii, yii):
    mny = max(yi-1, 0)
    mxy = min(yi+2, classmap.shape[0]-1)
    mnx = max(xi-1, 0)
    mxx = min(xi+2, classmap.shape[1]-1)
    choices = classmap[mny:mxy, mnx:mxx].flatten()
    choices = choices[choices != 0]
    if len(choices) == 0: continue
    selected = choices[np.random.randint(len(choices))]
    classmap[yi, xi] = selected
  is_shadow[classmap != old_classmap] = False
  return is_shadow

def segment(rgbimage):
  image = rgb2ybr(rgbimage)
  local_variance = varfilt(image, 5)
  mean = uniform_filter(image, (5, 5, 1))

  is_coral = (local_variance[:,:,0] < 10) & (mean[:,:,1] < mean[:,:,2]) & (mean[:,:,0] > 5) & (mean[:,:,2] > 130)  # & ~is_sand
  is_coral = morphology.binary_closing(is_coral, disk_strel(4))
  is_coral = alternating_sequence_filter(is_coral, 12)

  is_sand = (mean[:,:,0] > 130) & (local_variance[:,:,2] < 30) & (mean[:,:,1] > (mean[:,:,2]-20)) & ~is_coral
  is_sand = alternating_sequence_filter(is_sand, 8)
  
  is_shadow = (mean[:,:,0] < 30) & (local_variance[:,:,0] < 15) & ~is_coral & ~is_sand
  is_rubble = ~(is_coral | is_shadow | is_sand) & (local_variance[:,:,0] > 20)
  classmap = np.uint8(is_rubble*1 + is_sand*2 + is_coral*3)
  # Now fill shadow areas with somethin' else.
  #to_fill = classmap == 0
  #while to_fill.any():
  #  to_fill = fill_shadows(classmap, to_fill)
  return classmap

if __name__=='__main__':
  #for imgfile in sorted(glob.glob("/media/spanky/thesis-revision/datasets/B-504/*.png")):
  for imgfile in sorted(glob.glob('coral_imagery/TIFF/*.tif')):
    print "Segmenting", imgfile.rpartition("/")[2]
    img = np.asarray(Image.open(imgfile))
    mask = segment(img)
    imgfile = re.sub(r'.*/','output/',imgfile)
    imgfile = imgfile.replace(".tif","-mask.png")
    Image.fromarray(mask*80).save(imgfile)
    imgfile = imgfile.replace("png","gif")
    Image.fromarray(mask).save(imgfile)
    imgfile = imgfile.replace("gif","npy")
    np.save(imgfile, mask)
  
