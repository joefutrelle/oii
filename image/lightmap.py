from skimage import img_as_float, img_as_ubyte
from skimage.io import imread, imsave
from scipy.ndimage.filters import uniform_filter, gaussian_filter

def accumulate(image,sum_image=None,count=0):
    if sum_image is None:
        return (image, 1)
    else:
        sum_image += image
        return (sum_image, count+1)

def average_image(infiles):
    count, sum_image = 0, None
    for image_path in infiles:
        image = img_as_float(imread(image_path,plugin='freeimage'))
        (sum_image, count) = accumulate(image,sum_image,count)
    return sum_image / count

def learn_cfa(infiles,outfile,stereo=False,smooth=8):
    """Learn the average illumination for a set of RAW images.
    params:
    infiles - input files
    outfile - output file
    stereo - whether the files are L/R images or single images
    smooth - size of kernel for smoothing (0 for none)"""
    avg_image = average_image(infiles)
    (h,w) = avg_image.shape
    if smooth > 0:
        if stereo:
            xs,fw = [0,w/2], w/2
        else:
            xs,fw = [0], w
        for x in xs:
            for dy in [0,1]:
                for dx in [0,1]:
                    avg_image[dy::2,x+dx:x+dx+fw:2] = uniform_filter(avg_image[dy::2,x+dx:x+dx+fw:2],size=smooth,mode='nearest')
    imsave(outfile,avg_image)

def learn_rgb(infiles,outfile,stereo=False,smooth=4):
    """Learn the average illumiunation for a set of RGB images.
    params:
    infiles - input files
    outfile - output file
    stereo - whether the files are L/R images or single images
    smooth - size of kernel for smoothing (0 for none)"""
    avg_image = average_image(infiles)
    (h,w) = avg_image.shape
    if smooth > 0:
        if stereo:
            xs,fw = [0,w/2], w/2
        else:
            xs,fw = [0], w
        for x in xs:
            for c in range(3):
                avg_image[:,x:fw,c] = uniform_filter(avg_image[:,x:fw,c],size=smooth,mode='nearest')
    imsave(outfile,avg_image)
