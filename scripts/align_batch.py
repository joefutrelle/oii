import sys
import json
from urllib2 import urlopen

from skimage import img_as_float
from skimage.io import imread, imsave
from skimage.color import rgb2gray

from oii.image.demosaic import demosaic
from oii.iopipes import UrlSource, StagedInputFile
from oii.habcam.lightfield.quick import align, redcyan
from oii.utils import remove_extension

BASE_URL = 'http://pixel.whoi.edu:7722/'
BIN_PID = '201203.20120623.1150'
CAMERA_DISTANCE = 0.235
FOCAL_LENGTH = 0.012
H2O_ADJ = 1.25
PIXEL_DISTANCE = 0.00000645

CFA_PATTERN = 'rggb'

def list_images(bin_pid):
    for image in json.loads(urlopen('%s%s.json' % (BASE_URL, bin_pid)).read()):
        yield remove_extension(image['imagename'])

# pixels to meters
def p2m(offset):
    # FIXME hardcoded
    return (CAMERA_DISTANCE * FOCAL_LENGTH * H2O_ADJ) / (offset * PIXEL_DISTANCE)

bins = [
'201203.20120623.1220',
'201203.20120623.1100',
'201203.20120623.1110',
'201203.20120623.1120',
'201203.20120623.1130',
'201203.20120623.1140',
'201203.20120623.1150',
'201203.20120623.1200',
'201203.20120623.1210',
'201203.20120623.1230',
'201203.20120623.1240',
'201203.20120623.1250'
]

for bin_pid in bins:
    for imagename in list_images(bin_pid):
        image_url = '%s%s.tif' % (BASE_URL, imagename)
        with StagedInputFile(UrlSource(image_url)) as tif:
            imagedata = imread(tif,plugin='freeimage')
            cfa_LR = img_as_float(imagedata)
            #rgb_LR = demosaic(img_as_float(imagedata),pattern=CFA_PATTERN)
            #y_LR = rgb2gray(rgb_LR)
            # 'quick and dirty', based on rggb
            y_LR = cfa_LR[1::2,::2]
            (y,x) = align(y_LR)
            y *= 2
            x *= 2
            m = p2m(x)
            print '%s,%d,%d,%.2f' % (imagename,x,y,m) 
            sys.stdout.flush()
            #imsave('redcyan/%s.tif' % imagename, redcyan(y_LR))

