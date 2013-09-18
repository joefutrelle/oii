import numpy as np
from scipy.cluster.vq import kmeans2

def wh(img):
    return img.shape[:2] # surely there's some ndimage way to do this?

def np_random_choice(arr,ns):
    """this is an impl of a function that's not in numpy 1.7.x"""
    na = np.array(arr)
    return na[np.random.randint(na.size,size=ns)]

def random_sample(img,n_samples=None):
    if n_samples is None:
        n_samples = max(1,np.sum(wh(img)) / 2)
    return np_random_choice(img.reshape(img.size),n_samples)

def kmeans_image(img,k=2):
    (h,w,c) = img.shape
    iv = img.reshape(h*w,c)
    (means,labels) = kmeans2(iv,k)
    labeled = labels.reshape(h,w)
    out = np.zeros_like(img)
    for i in range(k):
        out[labeled==i,:] = means[i]
    return out
