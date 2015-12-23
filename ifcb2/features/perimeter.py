import numpy as np

from scipy.spatial.distance import pdist, squareform
from scipy import stats

def hist_stats(arr):
    """returns mean, median, skewness, and kurtosis"""
    arr = np.array(arr).flatten()
    mean = np.mean(arr)
    median = np.median(arr)
    skewness = stats.skew(arr)
    kurtosis = stats.kurtosis(arr,fisher=False)
    return mean, median, skewness, kurtosis
    
def perimeter_stats(points, equiv_diameter):
    """compute stats of pairwise distances
    between all given points, given an
    equivalent diameter.
    returns mean, median, skewness, and kurtosis
    """
    B = np.vstack(points).T
    # in H Sosik's version the square form is used,
    # use shorter form instead
    D = pdist(B) / equiv_diameter
    return hist_stats(D)
