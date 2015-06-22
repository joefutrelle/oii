from oii.ifcb import client
from oii.image import mosaic

# blob mask mosaic from http://ifcb-data.whoi.edu/mvco/IFCB5_2011_339_111025

def get_blobs(pid,limit=None):
    count = 0
    for target in client.list_targets(pid):
        count += 1
        if limit is not None and count > limit:
            return
        blob = target+'_blob.png'
        print 'fetching %s...' % blob
        yield client.fetch_image(blob)

PID='http://ifcb-data.whoi.edu/mvco/IFCB5_2011_339_111025'
print('loading images from %s...' % PID)
images = get_blobs(PID,500)
print 'laying out...'
layout = list(mosaic.layout(images, (2400, 2400000)))
print 'compositing...'
m = mosaic.composite(layout)
file='/Users/jfutrelle/Pictures/blob_mosaic.png'
print 'saving as %s...' % file
m.save(file,'PNG')

