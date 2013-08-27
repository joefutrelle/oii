import numpy as np
import os
import re

from skimage import img_as_float
from skimage.io import imsave, imread

from oii.image.lightmap import LearnLightmap

import logging

logging.basicConfig(format='%(asctime)s %(message)s')

OUTDIR='woah'

runs = {}

for n in range(128):
    lmp = os.path.join(OUTDIR,'lightmap_%d.png' % n)
    if os.path.exists(lmp):
        logging.warn('loading %s' % lmp)
        ai = img_as_float(imread(lmp))
        for i in range(1,n):
            run = 0
            for p in range(i,n-i):
                if ai[p-i,p] > 0.95:
                    run += 1
                else:
                    if run > 2:
                        logging.warn('%d; run of %d at %d and %d' % (n,run,p-run-i,p-run))
                        r = (run,p-run-i,p-run)
                        try:
                            runs[n] += [r]
                        except KeyError:
                            runs[n] = [r]
                    run = 0

exit

paths = []
with open('paths.txt') as pdt:
    for path in pdt:
        paths += [path.rstrip()]

lcp = len(os.path.commonprefix(paths))

on = 0
for path in paths:
    path = path[lcp:]
    n = len(path)
    if n == on:
        continue
    on = n
    try:
        rs = runs[n]
        logging.warn('runs for %d' % n)
        lp = list(path)
        vs = {}
        for v,(l,a,b) in zip(range(len(rs)),rs):
            vs[v] = ''.join(lp[a:a+l])
        out = ''
        sfx = ''
        suppress = 0
        for i,c in zip(range(len(lp)),lp):
            for v,(l,a,b) in zip(range(len(rs)),rs):
                if i==a:
                    sfx += ' ${v%d}=%s' % (v,vs[v])
                if i==a or i==b:
                    out += '${v%d}' % v
                    suppress = l
                    break
            if suppress <= 0:
                out += c
            suppress -= 1
        logging.warn('DONE %s' % path)
        logging.warn('DONE %s%s' % (out,sfx))
    except KeyError:
        logging.warn('no runs for %d' % n)
        pass


