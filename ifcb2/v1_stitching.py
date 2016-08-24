import numpy as np
from scipy.interpolate import Rbf

from oii.ifcb2.formats.adc import TRIGGER, LEFT, BOTTOM, WIDTH, HEIGHT
from oii.ifcb2.stitching import STITCHED, stitched_box, stitch_raw

# we don't use "real" eps, for backwards compatibility
_LEGACY_EPS = 0.000001

def normz(a):
    m = np.max(a) + _LEGACY_EPS
    return a / m

def avg(l):
    return sum(l) / len(l)

def mv(eh):
    eps = _LEGACY_EPS # no dividing by zero
    colors = np.arange(256)
    n = np.sum(eh) + eps
    s = np.sum(eh * colors)
    mean = s / n
    variance = np.sum((colors - mean) ** 2 * eh) / n
    return (mean, variance)

# FIXME this is still too sensitive to lower modes
def bright_mv(image,mask=None):
    b = np.arange(257)
    if mask is not None:
        eh, _ = np.histogram(image[mask].ravel(),bins=b)
    else:
        eh, _ = np.histogram(image.ravel(),bins=b)
    return bright_mv_hist(eh)

_BMH_KERNEL = np.array([2,2,2,2,2,4,8,2,1,1,1,1,1])

def bright_mv_hist(histogram,exclude=[0,255]):
    histogram = np.array(histogram)
    histogram[np.array(exclude)] = 0
    # smooth the filter, preferring peaks with sharp declines on the higher luminance end
    peak = np.convolve(histogram,_BMH_KERNEL,'same')
    # now smooth that to eliminate noise
    peak = np.convolve(peak,np.ones(9),'same')
    # scale original signal to the normalized smoothed signal;
    # that will tend to deattenuate secondary peaks, and reduce variance of bimodal distros
    scaled = normz(peak)**20 * histogram
    # now compute mean and variance
    return mv(scaled)

def extract_background(image,estimated_background):
    bg_mask = image - estimated_background
    # now compute threshold from histogram
    h, _ = np.histogram(bg_mask, bins=np.arange(257))
    # reject dark part with threshold
    total = np.sum(h)
    running = np.cumsum(h)
    threshold = np.argmax(running > total * 0.95)
    table = np.zeros(256,dtype=np.uint8)
    table[threshold:] = 255
    bg_mask = np.take(table, bg_mask)
    m = np.logical_not(bg_mask)
    bg_mask[m] = image[m]
    return bg_mask

def mask(targets):
    (x,y,w,h) = stitched_box(targets)
    # now we swap width and height to rotate the image 90 degrees
    M = np.zeros((w,h),dtype=np.bool)
    for target in targets:
        rx = target[LEFT] - x
        ry = target[BOTTOM] - y
        M[rx:rx+target[WIDTH],ry:ry+target[HEIGHT]] = True
    return M

def edges_mask(targets,images):
    # compute bounds relative to the camera field
    (x,y,w,h) = stitched_box(targets)
    # now we swap width and height to rotate the image 90 degrees
    edges = mask(targets)
    # blank out a rectangle in the middle of the rois
    inset_factor = 25
    insets = []
    for roi in targets:
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        insets += [roi[WIDTH] / inset_factor, roi[HEIGHT] / inset_factor]
    inset = np.sum(insets) / len(insets) # integer division
    for roi in targets:
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        edges[rx + inset : rx + roi[WIDTH] - inset - 1, ry + inset : ry + roi[HEIGHT] - inset - 1] = False
    return edges

def stitch(targets,images):
    # compute bounds relative to the camera field
    (x,y,w,h) = stitched_box(targets)
    # note that w and h are switched from here on out to rotate 90 degrees.
    # step 1: compute masks
    s = stitch_raw(targets,images,(x,y,w,h)) # stitched ROI's with black gaps
    rois_mask = mask(targets) # a mask of where the ROI's are
    gaps_mask = rois_mask == False # its inverse is where the gaps are
    edges = edges_mask(targets,images) # edges are pixels along the ROI edges
    # step 2: estimate background from edges
    # compute the mean and variance of the edges
    mean, variance = bright_mv(s,edges)
    # now use that as an estimated background
    s[gaps_mask] = mean
    # step 3: compute "probable background": low luminance delta from estimated bg
    flat_bg = np.full((w,h),mean,dtype=np.uint8)
    bg = extract_background(s,flat_bg)
    # also mask out the gaps, which are not "probable background"
    bg[gaps_mask] = 255
    # step 3a: improve mean/variance estimate
    mean, variance = bright_mv(bg)
    std_dev = np.sqrt(variance)
    # step 4: sample probable background to compute RBF for illumination gradient
    # grid
    div = 6 
    means, nodes = [], []
    rad = avg([h,w]) / div
    rad_step = int(rad/2)+1
    for x in range(0,h+rad,rad):
        for y in range(0,w+rad,rad):
            for r in range(rad,max(h,w),int(rad/3)+1):
                x1,y1,x2,y2 = (max(0,x-r),max(0,y-r),min(h-1,x+r),min(w-1,y+r))
                region = bg[y1:y2,x1:x2]
                nabe, _ = np.histogram(region, bins=np.arange(257))
                (m,v) = bright_mv_hist(nabe)
                if m > 0 and m < 255: # reject outliers
                    nodes.append((x,y))
                    means.append(m)
                    break
    # now construct radial basis functions for mean, based on the samples
    mean_rbf = Rbf([x for x,y in nodes], [y for x,y in nodes], means, epsilon=rad)
    # step 5: fill gaps with mean based on RBF and variance from bright_mv(edges)
    np.random.seed(0)
    noise = np.full((w,h),mean)
    mx, my = np.where(gaps_mask)
    noise[mx, my] = mean_rbf(my, mx)
    std_dev *= 0.66 # err on the side of smoother rather than noisier
    gaussian = np.random.normal(0, std_dev, size=mx.shape[0])
    noise[mx, my] += gaussian
    # step 6: final composite
    s[gaps_mask] = noise[gaps_mask]
    return s, rois_mask
