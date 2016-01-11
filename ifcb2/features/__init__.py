import numpy as np

from skimage.measure import regionprops

from oii.utils import imemoize

from oii.ifcb2.features.segmentation import segment_roi
from oii.ifcb2.features.blobs import find_blobs, rotate_blob
from oii.ifcb2.features.blob_geometry import equiv_diameter, ellipse_properties, \
    invmoments, convex_hull, convex_hull_image, convex_hull_perimeter
from oii.ifcb2.features.morphology import find_perimeter
from oii.ifcb2.features.biovolume import distmap_volume, sor_volume
from oii.ifcb2.features.perimeter import perimeter_stats, hausdorff_symmetry
from oii.ifcb2.features.texture import statxture, masked_pixels, texture_pixels
from oii.ifcb2.features.hog import image_hog

class Blob(object):
    def __init__(self,blob_image,roi_image):
        """roi_image should be the same size as the blob image,
        so a sub-roi"""
        self.image = np.array(blob_image).astype(np.bool)
        self.roi_image = roi_image
    @property
    def shape(self):
        return self.image.shape
    @property
    def size(self):
        return self.image.size
    @property
    @imemoize
    def pixels(self):
        """all pixel values, as a flat list"""
        return masked_pixels(self.roi_image, self.image)
    @property
    @imemoize
    def texture_pixels(self):
        """all pixel values of the contrast-enhanced image, as a flat list"""
        return texture_pixels(self.roi_image, self.image)
    @property
    @imemoize
    def regionprops(self):
        return regionprops(self.image)[0]
    @property
    @imemoize
    def area(self):
        return self.regionprops.area
    @property
    @imemoize
    def equiv_diameter(self):
        return self.regionprops.equivalent_diameter
    @property
    @imemoize
    def extent(self):
        return self.regionprops.extent
    @property
    @imemoize
    def convex_hull(self):
        return convex_hull(self.perimeter_points)
    @property
    @imemoize
    def convex_perimeter(self):
        return convex_hull_perimeter(self.convex_hull)
    @property
    @imemoize
    def convex_hull_image(self):
        return convex_hull_image(self.convex_hull, self.shape)
    @property
    @imemoize
    def convex_area(self):
        return np.sum(self.convex_hull_image)
    @property
    @imemoize
    def major_axis_length(self):
        return self.regionprops.major_axis_length
    @property
    @imemoize
    def minor_axis_length(self):
        return self.regionprops.minor_axis_length
    @property
    @imemoize
    def eccentricity(self):
        return self.regionprops.eccentricity
    @property
    @imemoize
    def orientation(self):
        """return orientation in degrees"""
        return (180/np.pi) * self.regionprops.orientation
    @property
    @imemoize
    def solidity(self):
        return float(self.area) / self.convex_area
    @property
    @imemoize
    def rotated_image(self):
        return rotate_blob(self.image, self.orientation)
    @property
    @imemoize
    def perimeter_image(self):
        return find_perimeter(self.image)
    @property
    @imemoize
    def perimeter_points(self):
        return np.where(self.perimeter_image)
    @property
    @imemoize
    def distmap_volume(self):
        return distmap_volume(self.image, self.perimeter_image)
    @property
    @imemoize
    def sor_volume(self):
        return sor_volume(self.rotated_image)
    @property
    @imemoize
    def biovolume_and_transect(self):
        area_ratio = float(self.convex_area) / self.area
        p = self.equiv_diameter / self.major_axis_length
        if area_ratio < 1.2 or (self.eccentricity < 0.8 and p > 0.8):
            return self.sor_volume, 0
        else:
            return self.distmap_volume
    @property
    @imemoize
    def biovolume(self):
        return self.biovolume_and_transect[0]
    @property
    @imemoize
    def rep_transect(self):
        """representative transect length"""
        return self.biovolume_and_transect[1]
    @property
    @imemoize
    def invmoments(self):
        return invmoments(self.image)
    @property
    @imemoize
    def phi(self,n):
        """invmoments"""
        return self.invmoments[n-1]
    @property
    @imemoize
    def perimeter_stats(self):
        """mean, median, skewness, kurtosis of perimeter points"""
        return perimeter_stats(self.perimeter_points, self.equiv_diameter)
    @property
    @imemoize
    def perimeter_mean(self):
        return self.perimeter_stats[0]
    @property
    @imemoize
    def perimeter_median(self):
        return self.perimeter_stats[1]
    @property
    @imemoize
    def perimeter_skewness(self):
        return self.perimeter_stats[2]
    @property
    @imemoize
    def perimeter_kurtosis(self):
        return self.perimeter_stats[3]
    @property
    @imemoize
    def texture_stats(self):
        """mean intensity, avg contrast, smoothness,
        third moment, uniformity, entropy of pixels"""
        return statxture(self.texture_pixels)
    @property
    @imemoize
    def texture_average_gray_level(self):
        return self.texture_stats[0]
    @property
    @imemoize
    def texture_average_contrast(self):
        return self.texture_stats[1]
    @property
    @imemoize
    def texture_smoothness(self):
        return self.texture_stats[2]
    @property
    @imemoize
    def texture_third_moment(self):
        return self.texture_stats[3]
    @property
    @imemoize
    def texture_uniformity(self):
        return self.texture_stats[4]
    @property
    @imemoize
    def texture_entropy(self):
        return self.texture_stats[5]
    @property
    @imemoize
    def hausdorff_symmetry(self):
        return hausdorff_symmetry(self.rotated_image)
        
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
        cropped_rois = [self.image[bbox] for bbox in bboxes]
        Bs = [Blob(b,R) for b,R in zip(blobs,cropped_rois)]
        return sorted(Bs, key=lambda B: B.area, reverse=True)
    @property
    @imemoize
    def hog(self):
        return image_hog(self.image)
