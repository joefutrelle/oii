import numpy as np
from numpy import convolve, median
from scipy import interpolate
from math import sqrt
from PIL import Image, ImageChops, ImageDraw
from oii.ifcb.formats.adc import TRIGGER, LEFT, BOTTOM, WIDTH, HEIGHT

def overlaps(t1, t2):
    if t1[TRIGGER] == t2[TRIGGER]:
        (x11, y11) = (t1[LEFT], t1[BOTTOM])
        (x12, y12) = (x11 + t1[WIDTH], y11 + t1[HEIGHT])
        (x21, y21) = (t2[LEFT], t2[BOTTOM])
        (x22, y22) = (x21 + t2[WIDTH], y21 + t2[HEIGHT])
        return x11 < x22 and x12 > x21 and y11 < y22 and y12 > y21
    return False

def find_pairs(targets):
    prev = None
    for target in targets:
        if prev is not None and overlaps(target, prev):
            yield (prev, target)
        prev = target

def normz(a):
    m = max(a) + 0.000001 # dividing by zero is bad
    return [float(x) / float(m) for x in a]

def avg(l):
    return sum(l) / len(l)
    
def mv(eh):
    n = 0.000001 # no dividing by zero
    sum = 0
    counts = zip(range(256), eh)
    for color,count in counts:
        n += count
        sum += count * color
    mean = sum / n
    sum2 = 0
    for color,count in counts:
        sum2 += ((color - mean) ** 2) * count
    variance = sum2 / n
    return (mean, variance)

# FIXME this is still too sensitive to lower modes
def bright_mv(image,mask=None):
    eh = image.histogram(mask)
    # toast extrema
    return bright_mv_hist(eh)

def bright_mv_hist(histogram,exclude=[0,255]):
    for x in exclude:
        histogram[x] = 0 
    # smooth the filter, preferring peaks with sharp declines on the higher luminance end
    peak = convolve(histogram,[2,2,2,2,2,4,8,2,1,1,1,1,1],'same')
    # now smooth that to eliminate noise
    peak = convolve(peak,[1,1,1,1,1,1,1,1,1],'same')
    # scale original signal to the normalized smoothed signal;
    # that will tend to deattenuate secondary peaks, and reduce variance of bimodal distros
    scaled = [(x**20)*y for x,y in zip(normz(peak),histogram)] # FIXME magic number
    # now compute mean and variance of the scaled signal
    return mv(scaled)

def extract_background(image,estimated_background):
    bg_mask = ImageChops.difference(image,estimated_background)
    # now compute threshold from histogram
    h = bg_mask.histogram()
    # reject dark part with threshold
    total = sum(h)
    running = 0
    for t in range(256):
        running += h[t]
        if running > total * 0.95:
            threshold = t
            break
    table = range(256)
    for t in range(256):
        if t < threshold:
            table[t] = 0
        else:
            table[t] = 255;
    bg_mask = bg_mask.point(table)
    bg_mask = ImageChops.screen(image,bg_mask)
    return bg_mask

def stitched_box(targets):
    # compute bounds relative to the camera field
    x = min([target[LEFT] for target in targets])
    y = min([target[BOTTOM] for target in targets])
    w = max([target[LEFT] + target[WIDTH] for target in targets]) - x
    h = max([target[BOTTOM] + target[HEIGHT] for target in targets]) - y
    return (x,y,w,h)

def mask(targets):
    (x,y,w,h) = stitched_box(targets)
    # now we swap width and height to rotate the image 90 degrees
    mask = Image.new('L',(h,w), 0) # a mask of the non-missing region
    for target in targets:
        rx = target[LEFT] - x
        ry = target[BOTTOM] - y
        mask.paste(255, (ry, rx, ry + target[HEIGHT], rx + target[WIDTH]))
    return mask

# stitch with no noise fill
def stitch_raw(targets,images,box=None,background=0):
    # compute bounds relative to the camera field
    if box is None:
        box = stitched_box(targets)
    (x,y,w,h) = box
    # now we swap width and height to rotate the image 90 degrees
    s = Image.new('L',(h,w),background) # the stitched image with a missing region
    for (roi,image) in zip(targets,images):
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        rw = roi[WIDTH]
        rh = roi[HEIGHT]
        roi_box = (ry, rx, ry + rh, rx + rw)
        s.paste(image, roi_box) # paste in the right location
    return s

def edges_mask(targets,images):
    # compute bounds relative to the camera field
    (x,y,w,h) = stitched_box(targets)
    # now we swap width and height to rotate the image 90 degrees
    edges = Image.new('L',(h,w), 0) # just the edges of the missing region
    draw = ImageDraw.Draw(edges)
    for (roi,image) in zip(targets,images):
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        edges.paste(255, (ry, rx, ry + roi[HEIGHT], rx + roi[WIDTH]))
    # blank out a rectangle in the middle of the rois
    inset_factor = 25
    insets = []
    for roi in targets:
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        insets += [roi[WIDTH] / inset_factor, roi[HEIGHT] / inset_factor]
    inset = avg(insets)
    for roi in targets:
        rx = roi[LEFT] - x
        ry = roi[BOTTOM] - y
        draw.rectangle((ry + inset, rx + inset, ry + roi[HEIGHT] - inset - 1, rx + roi[WIDTH] - inset - 1), fill=0)
    return edges

def euclidian(x1,y1,x2,y2):
    return sqrt(((x1 - x2) ** 2) + ((y1 - y2) ** 2))

def concentric(l):
    n = len(l)
    even = [l[i] for i in range(n) if i % 2 == 0]
    odd = [l[i] for i in range(n) if i % 2 != 0]
    for (one,two) in zip(even,reversed(odd)):
        yield one
        yield two

def hist(samples):
    h = [0 for ignore in range(256)]
    for s in samples:
        h[s] += 1
    return h

def stitch(targets,images):
    # compute bounds relative to the camera field
    (x,y,w,h) = stitched_box(targets)
    # note that w and h are switched from here on out to rotate 90 degrees.
    # step 1: compute masks
    s = stitch_raw(targets,images,(x,y,w,h)) # stitched ROI's with black gaps
    rois_mask = mask(targets) # a mask of where the ROI's are
    gaps_mask = ImageChops.invert(rois_mask) # its inverse is where the gaps are
    edges = edges_mask(targets,images) # edges are pixels along the ROI edges
    # step 2: estimate background from edges
    # compute the mean and variance of the edges
    (mean,variance) = bright_mv(s,edges)
    # now use that as an estimated background
    flat_bg = Image.new('L',(h,w),mean) # FIXME
    s.paste(mean,None,gaps_mask)
    # step 3: compute "probable background": low luminance delta from estimated bg
    bg = extract_background(s,flat_bg)
    # also mask out the gaps, which are not "probable background"
    bg.paste(255,None,gaps_mask)
    # step 3a: improve mean/variance estimate
    (mean,variance) = bright_mv(bg)
    std_dev = sqrt(variance)
    # step 4: sample probable background to compute RBF for illumination gradient
    # grid
    div = 6
    means = []
    nodes = []
    rad = avg([h,w]) / div
    rad_step = int(rad/2)+1
    for x in range(0,h+rad,rad):
        for y in range(0,w+rad,rad):
            for r in range(rad,max(h,w),int(rad/3)+1):
                box = (max(0,x-r),max(0,y-r),min(h-1,x+r),min(w-1,y+r))
                region = bg.crop(box)
                nabe = region.histogram()
                (m,v) = bright_mv_hist(nabe)
                if m > 0 and m < 255: # reject outliers
                    nodes.append((x,y))
                    means.append(m)
                    break
    # now construct radial basis functions for mean, based on the samples
    mean_rbf = interpolate.Rbf([x for x,y in nodes], [y for x,y in nodes], means, epsilon=rad)
    # step 5: fill gaps with mean based on RBF and variance from bright_mv(edges)
    mask_pix = gaps_mask.load()
    noise = Image.new('L',(h,w),mean)
    noise_pix = noise.load()
    np.random.seed(0)
    gaussian = np.random.normal(0, 1.0, size=(h,w)) # it's normal
    std_dev *= 0.66 # err on the side of smoother rather than noisier
    mask_x = []
    mask_y = []
    for x in xrange(h):
        for y in xrange(w):
            if mask_pix[x,y] == 255: # only for pixels in the mask
                mask_x.append(x)
                mask_y.append(y)
    rbf_fill = mean_rbf(np.array(mask_x), np.array(mask_y))
    for x,y,r in zip(mask_x, mask_y, rbf_fill):
        # fill is illumination gradient + noise
        noise_pix[x,y] = r + (gaussian[x,y] * std_dev)
    # step 6: final composite
    s.paste(noise,None,gaps_mask)
    return (s,rois_mask)

