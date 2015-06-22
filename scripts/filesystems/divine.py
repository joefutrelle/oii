import numpy as np
import os

from skimage.io import imsave

from oii.image.lightmap import LearnLightmap

OUTDIR='woah'

lightmaps = {}

def outmaps():
    for n in lightmaps.keys():
        lightmap = lightmaps[n]
        ai = lightmap.average_image()
        imsave(os.path.join(OUTDIR,'lightmap_%d.png' % n),ai * 1.)

paths = []
with open('paths.txt') as pdt:
    for path in pdt:
        paths += [path.rstrip()]

cp = os.path.commonprefix(paths)
lcp = len(cp)

stop = 0
for path in paths:
    path = path[lcp:]
    n = len(path)
    if n == 0:
        continue
    print path
    try:
        lightmap = lightmaps[n]
    except KeyError:
        lightmap = LearnLightmap(raw=True)
        lightmaps[n] = lightmap
    img = np.zeros((n,n),float)
    for yc,y in zip(path,range(n)):
        for xc,x in zip(path,range(n)):
            if xc==yc:
                img[y,x] = 1.
    lightmap.add_image(img)
    stop += 1
    if stop > 10000:
        outmaps()
        stop = 0

outmaps()

for n in lightmaps.keys():
    print 'lightmap %d' % n
    ai = lightmaps[n].average_image()
    for i in range(1,n):
        run = 0
        for p in range(i,n-i):
            if ai[p-i,p] == 1:
                run += 1
            else:
                if run > 2:
                    print 'run of %d at %d and %d' % (run,p-run-i,p-run)
                run = 0
    
