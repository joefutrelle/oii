import numpy as np
import scipy.ndimage as ndi

def resize(img,shape,order=0):
    """Resize using ndi zoom. Corrects for:
    http://scipy-user.10969.n7.nabble.com/wrong-output-shape-calculation-in-scipy-ndimage-interpolation-zoom-td17289.html"""
    if len(img.shape)==3:
        return np.dstack([resize(img[:,:,c],shape,order) for c in range(img.shape[2])])
    else:
        sy = (1. * shape[0] / img.shape[0]) + 0.0000000001
        sx = (1. * shape[1] / img.shape[1]) + 0.0000000001
        return ndi.interpolation.zoom(img,(sy,sx),order=order)
        return ndi.interpolation.zoom(img,1. * shape / img.shape,order=order)

def rescale(img,scale,order=0):
    new_size = [int(a * scale) for a in img.shape[:2]]
    return resize(img,new_size,order)
