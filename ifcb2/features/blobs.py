import numpy as np

from scipy.ndimage import measurements

from skimage.transform import rotate
from skimage.morphology import binary_closing, binary_dilation

from oii.ifcb2.features.morphology import SE2, SE3, EIGHT, bwmorph_thin

def label_blobs(B):
    B = np.array(B).astype(np.bool)
    labeled, _ = measurements.label(B,structure=EIGHT)
    objects = measurements.find_objects(labeled)
    return labeled, objects
    
def find_blobs(B):
    """find and return all blobs in the image, using
    eight-connectivity. returns a labeled image, the
    bounding boxes of the blobs, and the blob masks cropped
    to those bounding boxes"""
    B = np.array(B).astype(np.bool)
    labeled, objects = label_blobs(B)
    blobs = [labeled[obj]==ix+1 for ix, obj in zip(range(len(objects)), objects)]
    return labeled, objects, blobs

def rotate_blob(blob, theta):
    """rotate a blob and smooth out rotation artifacts"""
    blob = rotate(blob,-1*theta,resize=True)
    blob = binary_closing(blob,SE3)
    blob = binary_dilation(blob,SE2)
    blob = bwmorph_thin(blob,1)
    return blob

