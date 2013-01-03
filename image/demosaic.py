import numpy as np
from scipy.ndimage.filters import convolve

def CONV(i,w):
    return convolve(i, weights=w, mode='nearest')

def demosaic_bilinear(cfa,pattern='rggb'):
    # pull color channels
    ch = dict((c,np.zeros_like(cfa)) for c in 'rgb')
    for c,(y,x) in zip(pattern,[(0,0),(0,1),(1,0),(1, 1)]):
        ch[c][y::2,x::2] = cfa[y::2,x::2]
    (r,g,b) = (ch[c] for c in 'rgb')
    # interpolate per-channel
    (_,a,A) = (0., 0.25, 0.5)
    # kernel for sparsely-sampled channels (R and B)
    sintpl = [[a, A, a],
              [A, _, A],
              [a, A, a]]
    # kernel for densely-sampled channel (G)
    dintpl = [[_, a, _],
              [a, _, a],
              [_, a, _]]
    # convolve with channel-appropriate kernels
    r = np.where(r > 0, r, CONV(r, sintpl))
    g = np.where(g > 0, g, CONV(g, dintpl))
    b = np.where(b > 0, b, CONV(b, sintpl))
    return np.dstack((r,g,b))

def demosaic_gradient(cfa,pattern='rggb'):
    """Based on Laroche-Prescott"""

    # pull G channel
    offsets = [(0,0),(0,1),(1,0),(1,1)]
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
        a = np.abs(CONV(c,kernel))
        b = np.abs(CONV(c,np.rot90(kernel)))
        o = np.zeros_like(cfa)
        o[m::2,n::2] = (a < b)
        # produce two luminance estimates, one for each axis
        kernel = [[0.5, 0, 0.5]]
        h = CONV(cfa,kernel)
        v = CONV(cfa,np.rot90(kernel))
        # weight luminance estimates according to edge orientation
        e = (o * h) + ((1 - o) * v)
        g[m::2,n::2] = e[m::2,n::2]

    # interpolation kernel w for difference channel
    (a,A) = (0.25, 0.5)
    w = [[a, A, a],
         [A, 1, A],
         [a, A, a]]

    rb = {}
    # estimate R and B channel C by as g + (C - g) * w
    for ch,(m,n) in rb_offsets: # over R and B
        # pull color channel C
        c = np.zeros_like(cfa)
        c[m::2,n::2] = cfa[m::2,n::2]
        # generate difference channel C - g
        d = np.zeros_like(cfa)
        d[m::2,n::2] = (c - g)[m::2,n::2]
        # estimate C as g + (C - g) * w
        e = g + CONV(d, w)
        # add back in originally sampled data
        e[m::2,n::2] = cfa[m::2,n::2]
        rb[ch] = e
    
    return np.dstack((rb['r'], g, rb['b'])).clip(0.,1.)

def demosaic_hq_linear(cfa,pattern='rggb'):
    # Malvar et al
    # pull color channels
    offsets = [(0,0),(0,1),(1,0),(1,1)]
    ch = dict((c,np.zeros_like(cfa)) for c in 'rgb')
    for c,(y,x) in zip(pattern,offsets):
        ch[c][y::2,x::2] = cfa[y::2,x::2]
    (R,G,B) = 'rgb'
    # compute offets of R and B channels
    rb_offsets = [(c,(m,n)) for c,(m,n) in zip(pattern,offsets) if c in 'rb']
    g_offsets = [(m,n) for c,(m,n) in zip(pattern,offsets) if c in 'g']

    # rb at br locations, other color
    rbk = np.array([[   0, 0, -1.5, 0,    0],
                    [   0, 0,    0, 0,    0],
                    [-1.5, 0,    6, 0, -1.5],
                    [   0, 0,    0, 0,    0],
                    [   0, 0, -1.5, 0,    0]]) / 8.
    # rb at br locations, same color
    brk = np.array([[2, 0, 2],
                    [0, 0, 0],
                    [2, 0, 2]]) / 8.
    # rb at g locations, other color (horizontal)
    cgck = np.array([[4, 0, 4]]) / 8.
    cgck_90 = np.rot90(cgck)
    # rb at g locations, g (horizontal)
    cgk = np.array([[ 0 , 0, 0.5,  0,  0],
                    [ 0, -1,   0, -1,  0],
                    [-1 , 0,   5,  0, -1],
                    [ 0, -1,   0, -1,  0],
                    [ 0,  0, 0.5,  0,  0]]) / 8.
    cgk_90 = np.rot90(cgk)

    for c,(i,j) in rb_offsets:
        for (m,n) in g_offsets:
            # RB at green pixel
            wc, wg = (cgck,cgk) if m==i else (cgck_90,cgk_90)
            ch[c][m::2,n::2] = CONV(ch[c],wc)[m::2,n::2] + CONV(ch[G],wg)[m::2,n::2]
        # R at B, B at R
        (k,l) = (1-i, 1-j) # other offsets
        d = {R:B,B:R}[c] # other channel
        ch[c][k::2,l::2] = CONV(ch[d],rbk)[k::2,l::2] + CONV(ch[c],brk)[k::2,l::2]

    # estimate green
    ck = np.array([[0,  0, -1,  0,  0],
                   [0,  0,  0,  0,  0],
                   [-1, 0,  4,  0, -1],
                   [0,  0,  0,  0,  0],
                   [0,  0, -1,  0,  0]]) / 8.
    gk = np.array([[0, 2, 0],
                   [2, 0, 2],
                   [0, 2, 0]]) / 8.;
    
    gc = CONV(ch[G],gk)
    for c,(m,n) in rb_offsets:
        ch[G][m::2,n::2] = CONV(ch[c],ck)[m::2,n::2] + gc[m::2,n::2]
        
    rgb = np.dstack(ch[c] for c in 'rgb').clip(0.,1.)
    
    # now correct edge artifacts via linear interpolation
    rgb[:2,:] = demosaic_gradient(cfa[:6,:],pattern)[:2,:]
    rgb[-2:,:] = demosaic_gradient(cfa[-6:,:],pattern)[-2:,:]
    rgb[:,:2] = demosaic_gradient(cfa[:,:6],pattern)[:,:2]
    rgb[:,-2:] = demosaic_gradient(cfa[:,-6:],pattern)[:,-2:]
    
    return rgb

def demosaic(cfa,method='hq_linear',pattern='rggb'):
    if method=='hq_linear':
        return demosaic_hq_linear(cfa,pattern)
    if method=='gradient':
        return demosaic_gradient(cfa,pattern)
    elif method=='bilinear':
        return demosaic_bilinear(cfa,pattern)
