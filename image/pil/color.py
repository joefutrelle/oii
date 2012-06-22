from PIL import Image, ImageStat

def gray_world(img):
    """Gray world color correction algorithm.
    1. Compute mean on each channel
    2. Compute "gray" as mean of all 3 channels' means
    3. Scale each channel proportional to its contribution to gray"""
    stat = ImageStat.Stat(img)
    (mR, mG, mB) = stat.mean
    gray = (mR + mG + mB) / 3
    (R, G, B) = img.split()
    (gR, gG, gB) = [Image.eval(channel, lambda v: v * (gray / mean)) for mean,channel in zip((mR, mG, mB),(R, G, B))]
    return Image.merge('RGB', (gR, gG, gB))
