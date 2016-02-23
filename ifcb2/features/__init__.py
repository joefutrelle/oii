import numpy as np

from scipy.ndimage.measurements import find_objects

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
from oii.ifcb2.features.ringwedge import ring_wedge

class Blob(object):
    def __init__(self,blob_image,roi_image):
        """roi_image should be the same size as the blob image,
        so a sub-roi"""
        self.image = np.array(blob_image).astype(np.bool)
        self.roi_image = roi_image
    @property
    def shape(self):
        """h,w of blob image"""
        return self.image.shape
    @property
    def bbox_ywidth(self):
        return self.shape[0]
    @property
    def bbox_xwidth(self):
        return self.shape[1]
    @property
    def size(self):
        """h*w of blob image"""
        return self.image.size
    @property
    @imemoize
    def pixels(self):
        """all pixel values of pixels in blob, as a flat list"""
        return masked_pixels(self.roi_image, self.image)
    @property
    @imemoize
    def texture_pixels(self):
        """all pixel values of the contrast-enhanced image, in the blob,
        as a flat list"""
        return texture_pixels(self.roi_image, self.image)
    @property
    @imemoize
    def regionprops(self):
        """region props of the blob (assumes single connected region)"""
        return regionprops(self.image)[0]
    @property
    @imemoize
    def area(self):
        """area of blob"""
        return self.regionprops.area
    @property
    @imemoize
    def equiv_diameter(self):
        """equivalent diameter of blob"""
        return self.regionprops.equivalent_diameter
    @property
    @imemoize
    def extent(self):
        """extent of blob"""
        return self.regionprops.extent
    @property
    @imemoize
    def convex_hull(self):
        """vertices of convex hull of blob"""
        return convex_hull(self.perimeter_points)
    @property
    @imemoize
    def convex_perimeter(self):
        """perimeter of convex hull"""
        return convex_hull_perimeter(self.convex_hull)
    @property
    @imemoize
    def convex_hull_image(self):
        """convex hull mask"""
        return convex_hull_image(self.convex_hull, self.shape)
    @property
    @imemoize
    def convex_area(self):
        """area of convex hull (computed from mask)"""
        return np.sum(self.convex_hull_image)
    @property
    @imemoize
    def major_axis_length(self):
        """major axis length of blob"""
        return self.regionprops.major_axis_length
    @property
    @imemoize
    def minor_axis_length(self):
        """minor axis length of blob"""
        return self.regionprops.minor_axis_length
    @property
    @imemoize
    def eccentricity(self):
        """1st eccentricity of blob"""
        return self.regionprops.eccentricity
    @property
    @imemoize
    def orientation(self):
        """return orientation of blob in degrees"""
        return (180/np.pi) * self.regionprops.orientation
    @property
    @imemoize
    def solidity(self):
        """area / convex area of blob"""
        return float(self.area) / self.convex_area
    @property
    @imemoize
    def rotated_image(self):
        """blob rotated so major axis is horizontal. may
        not be touching edges of returned image"""
        return rotate_blob(self.image, self.orientation)
    @property
    @imemoize
    def rotated_area(self):
        """area of rotated blob"""
        return np.sum(self.rotated_image)
    @property
    @imemoize
    def rotated_shape(self):
        """height, width of rotated image's bounding box"""
        ys, xs = find_objects(self.rotated_image)[0]
        h = ys.stop - ys.start
        w = xs.stop - xs.start
        return h, w
    @property
    def rotated_bbox_xwidth(self):
        return self.rotated_shape[1]
    @property
    def rotated_bbox_ywidth(self):
        return self.rotated_shape[0]
    @property
    @imemoize
    def perimeter_image(self):
        """perimeter of blob defined via erosion and logical and"""
        return find_perimeter(self.image)
    @property
    @imemoize
    def perimeter_points(self):
        """points on the perimeter of the blob"""
        return np.where(self.perimeter_image)
    @property
    @imemoize
    def distmap_volume(self):
        """volume of blob computed via Moberg & Sosik algorithm"""
        return distmap_volume(self.image, self.perimeter_image)
    @property
    @imemoize
    def sor_volume(self):
        """volume of blob computed via solid of revolution method"""
        return sor_volume(self.rotated_image)
    @property
    @imemoize
    def biovolume_and_transect(self):
        """biovolume and representative transect computed using
        Moberg & Sosik algorithm"""
        area_ratio = float(self.convex_area) / self.area
        p = self.equiv_diameter / self.major_axis_length
        if area_ratio < 1.2 or (self.eccentricity < 0.8 and p > 0.8):
            return self.sor_volume, 0
        else:
            return self.distmap_volume
    @property
    @imemoize
    def biovolume(self):
        """biovolume computed using Moberg & Sosik algorithm"""
        return self.biovolume_and_transect[0]
    @property
    @imemoize
    def rep_transect(self):
        """representative transect length computed using Moberg & Sosik
        algorithm"""
        return self.biovolume_and_transect[1]
    @property
    @imemoize
    def invmoments(self):
        """invariant moments computed using algorithm described in
        Digital Image Processing Using MATLAB, pp. 470-472"""
        return invmoments(self.image)
    @property
    @imemoize
    def phi(self,n):
        """nth invariant moment (see invmoments)"""
        return self.invmoments[n-1]
    @property
    @imemoize
    def perimeter_stats(self):
        """mean, median, skewness, kurtosis of pairwise distances
        between each pair of perimeter points"""
        return perimeter_stats(self.perimeter_points, self.equiv_diameter)
    @property
    @imemoize
    def perimeter_mean(self):
        """mean of pairwise distances between perimeter points"""
        return self.perimeter_stats[0]
    @property
    @imemoize
    def perimeter_median(self):
        """median of pairwise distances between perimeter points"""
        return self.perimeter_stats[1]
    @property
    @imemoize
    def perimeter_skewness(self):
        """skewness of pairwise distances between perimeter points"""
        return self.perimeter_stats[2]
    @property
    @imemoize
    def perimeter_kurtosis(self):
        """kurtosis of pairwise distances between perimeter points"""
        return self.perimeter_stats[3]
    @property
    @imemoize
    def texture_stats(self):
        """mean intensity, average contrast, smoothness,
        third moment, uniformity, entropy of texture pixels.
        based on algorithm described in Digital Image Processing Using
        MATLAB, pp . 464-468.
        see texture_pixels"""
        return statxture(self.texture_pixels)
    @property
    @imemoize
    def texture_average_gray_level(self):
        """average gray level of texture pixels"""
        return self.texture_stats[0]
    @property
    @imemoize
    def texture_average_contrast(self):
        """average contrast of texture pixels"""
        return self.texture_stats[1]
    @property
    @imemoize
    def texture_smoothness(self):
        """smoothness of texture pixels"""
        return self.texture_stats[2]
    @property
    @imemoize
    def texture_third_moment(self):
        """third moment of texture pixels"""
        return self.texture_stats[3]
    @property
    @imemoize
    def texture_uniformity(self):
        """uniformity of texture pixels"""
        return self.texture_stats[4]
    @property
    @imemoize
    def texture_entropy(self):
        """entropy of texture pixels"""
        return self.texture_stats[5]
    @property
    @imemoize
    def hausdorff_symmetry(self):
        """takes the rotated blob perimeter and compares it
        with itself rotated 180 degrees, rotated 90 degrees,
        and mirrored across the major axis, using
        the modified Hausdorff distance between the rotated
        blob perimeter and each of those variants"""
        return hausdorff_symmetry(self.rotated_image)
    @property
    @imemoize
    def h180(self):
        return self.hausdorff_symmetry[0]
    @property
    @imemoize
    def h90(self):
        return self.hausdorff_symmetry[1]
    @property
    @imemoize
    def hflip(self):
        return self.hausdorff_symmetry[2]
    @property
    @imemoize
    def ring_wedge(self):
        pwr_integral, pwr_ratio, wedges, rings = ring_wedge(self.image)
        return pwr_integral, pwr_ratio, wedges, rings
    @property
    @imemoize
    def rw_power_integral(self):
        return self.ring_wedge[0]
    @property
    @imemoize
    def rw_power_ratio(self):
        return self.ring_wedge[1]
    @property
    @imemoize
    def wedge(self):
        return self.ring_wedge[2]
    @property
    @imemoize
    def ring(self):
        return self.ring_wedge[3]
        
class Roi(object):
    def __init__(self,roi_image):
        self.image = np.array(roi_image).astype(np.uint8)
    @property
    @imemoize
    def blobs_image(self):
        """return the mask resulting from segmenting the image using
        the algorithm in oii.ifcb2.features.segmentation.segment_roi"""
        return segment_roi(self.image)
    @property
    @imemoize
    def blobs(self):
        """returns the Blob objects representing each of the blobs in
        the segmented mask, ordered by largest area to smallest area"""
        labeled, bboxes, blobs = find_blobs(self.blobs_image)
        cropped_rois = [self.image[bbox] for bbox in bboxes]
        Bs = [Blob(b,R) for b,R in zip(blobs,cropped_rois)]
        return sorted(Bs, key=lambda B: B.area, reverse=True)
    @property
    def num_blobs(self):
        return len(self.blobs)
    @property
    @imemoize
    def hog(self):
        """returns the Histogram of Oriented Gradients of the image.
        see oii.ifcb2.features.hog"""
        return image_hog(self.image)



