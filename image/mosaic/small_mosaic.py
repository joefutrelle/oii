from oii.ifcb import client
from oii.image import mosaic
import os
import re
from PIL import Image

DIR='/Users/jfutrelle/Pictures'

def get_images():
    for filename in os.listdir(DIR):
        if re.match(r'.*\.png$',filename) or re.match(r'.*\.jpg$',filename):
            file = os.path.join(DIR,filename)
            image = Image.open(file)
            if image.size[0] < 1024 and image.size[1] < 1024:
                print 'including %s...' % filename
                yield image
                
images = list(get_images())
print 'laying out...'
layout = list(mosaic.layout(images, (5000, 2400000)))
print layout
print 'compositing...'
m = mosaic.composite(layout,None,'RGB')
file='/Users/jfutrelle/Pictures/a_mosaic.jpg'
print 'saving as %s...' % file
m.save(file,'JPEG')
print 'done'

