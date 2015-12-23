from skimage.morphology import convex_hull_image

from oii.ifcb2.features import BLOB_IMAGE, BOUNDING_BOX, EQUIV_DIAMETER, \
    EXTENT, CONVEX_HULL_IMAGE, CONVEX_AREA, FERET_DIAMETER, MAJOR_AXIS_LENGTH, \
    MINOR_AXIS_LENGTH, ECCENTRICITY, ORIENTATION, ROTATED_BLOB_IMAGE
from oii.ifcb2.features.blobs import find_blobs, rotate_blob

from oii.ifcb2.features.blob_geometry import equiv_diameter, ellipse_parameters

def blob_features(blob_image):
    labeled, bboxes, blobs = find_blobs(blob_image)
    Fs = [{
        BLOB_IMAGE: B,
        BOUNDING_BOX: bbox
        CONVEX_HULL_IMAGE: convex_hull_image(B)
    } for B,bbox in zip(blobs,bboxes)]
    for B,F in zip(blobs,Fs):
        area = np.sum(B)
        F[AREA] = area
        F[EQUIV_DIAMETER] = equiv_diameter(area)
        F[EXTENT] = float(area) / B.size
        hull = F[CONVEX_HULL_IMAGE]
        convex_area = blob_area(hull)
        F[CONVEX_AREA] = blob_area(hull)
        F[FERET_DIAMETER] = np.max(hull.flatten())
        maj_axis, min_axis, ecc, orientation = ellipse_parameters(B)
        F[MAJOR_AXIS_LENGTH] = maj_axis
        F[MINOR_AXIS_LENGTH] = min_axis
        F[ORIENTATION] = orientation
        F[ECCENTRICITY] = ecc
        F[SOLIDITY] = float(area) / convex_area
        F[ROTATED_BLOB_IMAGE] = rotate_blob(B,orientation)

    
