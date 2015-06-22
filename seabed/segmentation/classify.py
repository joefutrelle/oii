#!/usr/bin/env python
import Image, ImageChops
import numpy as N
from scipy.ndimage import morphology

def disk_strel(radius):
  # Dimensions of (square) structuring element
  sz = 2*radius + 1
  # Return mask of points whose centers are no further away than 'radius'
  x,y = N.mgrid[:sz,:sz]
  return N.sqrt((x-radius)**2 + (y-radius)**2) <= radius

def jeff_coral_finder(im, sand_intensity_threshold, coral_gradient_threshold,
                      maximum_altseqfilt_radius, shadow_discriminant_threshold,
                      shadow_discriminant_scaling):
  im_grey = N.asarray(im.convert("L"))
  im = N.asarray(im)
  dot = N.array([[0,1,0], [1,1,1], [0,1,0]])
  dilated = morphology.grey_dilation(im_grey, dot.shape, structure=dot)
  eroded = morphology.grey_erosion(im_grey, dot.shape, structure=dot)
  gradient = dilated - eroded
  fisher_discriminant = N.dot(im, shadow_discriminant_scaling)

  # Make initial class determinations.
  is_shadow = fisher_discriminant < shadow_discriminant_threshold
  is_sand   = im_grey > sand_intensity_threshold
  is_smooth = gradient < coral_gradient_threshold
  is_coral  = is_smooth & ~is_sand & ~is_shadow

  # Now perform an alternating sequence filter on coral,
  for radius in range(1, maximum_altseqfilt_radius+1):
    se = disk_strel(radius)
    opened = morphology.binary_opening(is_coral, se)
    is_coral = morphology.binary_closing(opened, se)
  # Now perform an alternating sequence filter on sand.
  for radius in range(1, maximum_altseqfilt_radius+1):
    se = disk_strel(radius)
    opened = morphology.binary_opening(is_sand, se)
    is_sand = morphology.binary_closing(opened, se)
  # Use coral mask to exclude sand.
  is_sand = is_sand & ~is_coral
  return is_sand, is_coral

import glob
#for fname in sorted(glob.glob("/media/spanky/thesis-revision/datasets/B/*.png")):
for fname in sorted(glob.glob("./coral_imagery/TIFF/*.tif")):
  print fname
  img = Image.open(fname)
  # Values from SSF work
  #sand, coral = jeff_coral_finder(img, 205, 15, 8, 85, [.33333,.33333,.33333])
  # Values from Training set
  #sand, coral = jeff_coral_finder(img, 189, 11, 8, 50.4858, [.7762,.2288,-.5874])

  # Chris's values for dataset B
  sand, coral = jeff_coral_finder(img, 255, 30, 8, 30, [.3333, .3333,.3333])

  # Now generate a composite image.
  orange_mask = N.dstack((coral, coral, coral)) * [200, 168, 50]
  green_mask = N.dstack((sand, sand, sand)) * [255, 190, 190]
  green_mask[green_mask==0] = 255
  orange_mask = Image.fromarray(N.cast['uint8'](orange_mask))
  green_mask = Image.fromarray(N.cast['uint8'](green_mask))
  masked = ImageChops.multiply(img, green_mask)
  masked = ImageChops.screen(masked, orange_mask)
  new_fname = "output/masked-" + fname.rpartition("/")[2]
  print new_fname
  masked.save(new_fname)

