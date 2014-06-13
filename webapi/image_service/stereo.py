import sys
from skimage.io import imsave
from skimage.color import rgb2gray
from oii.image.io import imread
from oii.image.stereo import get_L, get_R, redcyan
from oii.resolver import parse_stream
import fileinput

def get_img(hit):
    if hit is None:
        raise
    img = imread(hit.value)
    if hit.product == 'LR':
        return img
    elif hit.product == 'R':
        return get_R(img)
    elif hit.product == 'redcyan':
        return redcyan(rgb2gray(img),None,True)
    else:
        return get_L(img)

def get_resolver(path):
    """assumes there is a resolver called 'image'"""
    resolvers = parse_stream(path)
    return resolvers['image']






