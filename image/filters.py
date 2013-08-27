from scipy.ndimage.filters import gaussian_filter

def unsharp_mask(image,size,a=3):
    um = gaussian_filter(image,size)
    return (a / (a - 1)) * (image - um / a)
