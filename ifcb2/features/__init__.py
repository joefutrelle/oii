import numpy as np

from skimage.morphology import convex_hull_image

from oii.utils import imemoize

from oii.ifcb2.features.segmentation import segment_roi
from oii.ifcb2.features.blobs import find_blobs, rotate_blob
from oii.ifcb2.features.blob_geometry import equiv_diameter, ellipse_properties

class Blob(object):
    def __init__(self,blob_image):
        self.image = np.array(blob_image).astype(np.bool)
    @property
    @imemoize
    def convex_hull_image(self):
        return convex_hull_image(self.image)
    @property
    @imemoize
    def area(self):
        return np.sum(self.image)
    @property
    @imemoize
    def equiv_diameter(self):
        return equiv_diameter(self.area)
    @property
    @imemoize
    def extent(self):
        return float(self.area) / self.image.size
    @property
    @imemoize
    def convex_area(self):
        return np.sum(self.convex_hull_image)
    @property
    @imemoize
    def feret_diameter(self):
        return np.max(self.convex_hull_image.flatten())
    @property
    @imemoize
    def ellipse_properties(self):
        # major axis length, minor axis length, eccentricity, orientation
        return ellipse_properties(self.image)
        maj_axis, min_axis, ecc, orientation = ellipse_parameters(B)
    @property
    @imemoize
    def major_axis_length(self):
        return self.ellipse_properties[0]
    @property
    @imemoize
    def minor_axis_length(self):
        return self.ellipse_properties[1]
    @property
    @imemoize
    def eccentricity(self):
        return self.ellipse_properties[2]
    @property
    @imemoize
    def orientation(self):
        return self.ellipse_properties[3]
    @property
    @imemoize
    def solidity(self):
        return float(self.area) / self.convex_area
    @property
    @imemoize
    def rotated_image(self):
        return rotate_blob(self.image, self.orientation)
        
class Roi(object):
    def __init__(self,roi_image):
        self.image = np.array(roi_image).astype(np.uint8)
    @property
    @imemoize
    def blobs_image(self):
        return segment_roi(self.image)
    @property
    @imemoize
    def blobs(self):
        labeled, bboxes, blobs = find_blobs(self.blobs_image)
        return [Blob(B) for B in blobs]
