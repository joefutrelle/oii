"""
demosaic - converts color-filter-array images to RGB images

Copyright (c) 2013, Joe Futrelle (jfutrelle@whoi.edu)
All rights reserved.
 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import numpy as np
from scipy.ndimage.filters import convolve

def CONV(i,w):
    return convolve(i, weights=w, mode='reflect')

def demosaic_bilinear(cfa,pattern='rggb',clip=(0.,1.)):
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
    return np.dstack((r,g,b)).clip(clip[0],clip[1])

def demosaic_gradient(cfa,pattern='rggb',clip=(0.,1.)):
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
    
    return np.dstack((rb['r'], g, rb['b'])).clip(clip[0],clip[1])
                  
def demosaic_hq_linear(cfa,pattern='rggb',clip=(0.,1.)):
    # Malvar et al
    # kernel generation from bayer pattern
    def color_kern(pattern,c):
        return np.array([[pattern[0]==c, pattern[1]==c],
                         [pattern[2]==c, pattern[3]==c]])
    def r_kern(pattern):
        return color_kern(pattern,'r')
    def g_kern(pattern):
        return color_kern(pattern,'g')
    def b_kern(pattern):
        return color_kern(pattern,'b')
    def ratg_rrow_kern(pattern):
        gk = g_kern(pattern)
        return gk & np.array([[pattern[1]=='r', pattern[0]=='r'],
                              [pattern[3]=='r', pattern[2]=='r']])
    def ratg_rcol_kern(pattern):
        gk = g_kern(pattern)
        return gk & np.array([[pattern[2]=='r', pattern[3]=='r'],
                              [pattern[0]=='r', pattern[1]=='r']])

    # produce masks
    (h,w) = cfa.shape[:2]
    cells = np.ones((h/2,w/2)) # for producing masks

    r_mask = np.kron(cells, r_kern(pattern))
    g_mask = np.kron(cells, g_kern(pattern))
    b_mask = np.kron(cells, b_kern(pattern))

    # construct green channel
    G = cfa * g_mask

    # interpolate G at RB locations
    gatrb = np.array([[ 0, 0, -1, 0,  0],
                      [ 0, 0,  2, 0,  0],
                      [-1, 2,  4, 2, -1],
                      [ 0, 0,  2, 0,  0],
                      [ 0, 0, -1, 0,  0]]) / 8.

    G += CONV(image, gatrb) * (1-g_mask)

    # R and B channels
    R = cfa * r_mask
    B = cfa * b_mask

    # interpolate R at B locations and vice versa
    rbatbr = np.array([[   0, 0, -1.5, 0,    0],
                       [   0, 2,    0, 2,    0],
                       [-1.5, 0,    6, 0, -1.5],
                       [   0, 2,    0, 2,    0],
                       [   0, 0, -1.5, 0,    0]]) / 8.

    iRB = CONV(image, rbatbr)
    R += iRB * b_mask
    B += iRB * r_mask
    
    # now interpolate R and B at G locations

    # masks
    ratg_rrow_mask = np.kron(cells, ratg_rrow_kern(pattern))
    ratg_rcol_mask = np.kron(cells, ratg_rcol_kern(pattern))
    batg_brow_mask = ratg_rcol_mask
    batg_bcol_mask = ratg_rrow_mask

    # convolution kernels
    rbatg_rbrow = np.array([[ 0,  0, 0.5,  0,  0],
                            [ 0, -1,   0, -1,  0],
                            [-1,  4,   5,  4, -1],
                            [ 0, -1,   0, -1,  0],
                            [ 0,  0, 0.5,  0,  0]]) / 8.
    rbatg_rbcol = np.rot90(rbatg_rbrow)

    # RB at G in RB row, BR column
    iRB = CONV(image, rbatg_rbrow)
    R += iRB * ratg_rrow_mask
    B += iRB * batg_brow_mask

    # RB at G in BR row, RB column
    iRB = CONV(image, rbatg_rbcol)
    R += iRB * ratg_rcol_mask
    B += iRB * batg_bcol_mask

    # assemble color image and clip
    RGB = np.dstack([R,G,B]).clip(clip[0],clip[1])
    return RGB

def demosaic(cfa,pattern='rggb',method='hq_linear',clip=(0.,1.)):
    if method=='hq_linear':
        rgb = demosaic_hq_linear(cfa,pattern,clip)
    if method=='gradient':
        rgb = demosaic_gradient(cfa,pattern,clip)
    elif method=='bilinear':
        rgb = demosaic_bilinear(cfa,pattern,clip)
    return rgb
