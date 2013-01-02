import numpy as np
from scipy.ndimage.filters import convolve

def demosaic_bilinear(cfa,pattern='rggb'):
    ch = dict((c,np.zeros_like(cfa)) for c in 'rgb')
    for c,(y,x) in zip(pattern,[(0,0),(1,0),(0,1),(1, 1)]):
        ch[c][y::2,x::2] = im[y::2,x::2]
    (r,g,b) = (ch[c] for c in 'rgb')
    (_,a,A) = (0., 0.25, 0.5)
    sintpl = [[a, A, a],
              [A, _, A],
              [a, A, a]]
    dintpl = [[_, a, _],
              [a, _, a],
              [_, a, _]]
    r = np.where(r > 0, r, convolve(r, weights=sintpl))
    g = np.where(g > 0, g, convolve(g, weights=dintpl))
    b = np.where(b > 0, b, convolve(b, weights=sintpl))
    return np.dstack((r,g,b))

def demosaic_gradient(cfa,pattern='rggb'):
    """Based on Laroche-Prescott"""
    offsets = [(0,0),(1,0),(0,1),(1,1)]

    # pull G channel
    g = np.zeros_like(cfa)
    for c,(m,n) in zip(pattern,offsets):
        if c == 'g':
            g[m::2,n::2] = cfa[m::2,n::2]
    # compute offets of R and B channels
    rb_offsets = [(rb,(m,n)) for rb,(m,n) in zip(pattern,offsets) if rb in 'rb']

    # edge-sensitive estimation of missing G channel
    for _,(m,n) in rb_offsets: # for R and B channels
        c = cfa[m::2,n::2] # pull color channel
        # detect edge orientation
        kernel = [[0.5, -1, 0.5]]
        a = np.abs(convolve(c,weights=kernel))
        b = np.abs(convolve(c,weights=np.rot90(kernel)))
        o = np.zeros_like(cfa)
        o[m::2,n::2] = (a < b)
        # produce two luminance estimates, one for each axis
        kernel = [[0.5, 0, 0.5]]
        h = convolve(cfa,weights=kernel)
        v = convolve(cfa,weights=np.rot90(kernel))
        # weight luminance estimates according to edge orientation
        e = (o * h) + ((1 - o) * v)
        g[m::2,n::2] = e[m::2,n::2]

    (a,A) = (0.25, 0.5)
    w = [[a, A, a],
         [A, 1, A],
         [a, A, a]]

    rb = {}

    # estimate R and B channel C by as g + i(C - g)
    # where i denotes interpolating into missing regions
    for ch,(m,n) in rb_offsets:    
        c = np.zeros_like(cfa)
        c[m::2,n::2] = cfa[m::2,n::2]
        d = np.where(c > 0, c - g, 0)
        dc = convolve(d, weights=w)
        e = dc + g
        e[m::2,n::2] = c[m::2,n::2]
        rb[ch] = e.clip(0.,1.)
    
    return np.dstack((rb['r'], g, rb['b']))

def demosaic(cfa,method='gradient',pattern='rggb'):
    if method=='gradient':
        return demosaic_gradient(cfa,pattern)
    elif method=='bilinear':
        return demosaic_bilinear(cfa,pattern)
