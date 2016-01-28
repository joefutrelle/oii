import numpy as np
from scipy import stats

def get_flow(targets):
    if not targets: # no ROIs
        return 0 # unable to determine that this is bad flow
    X = np.array([p['left'] for p in targets])
    Y = np.array([p['bottom'] for p in targets])
    P = np.vstack((X,Y)).T

    # compute distances from centroid
    centroid = [np.mean(X), np.mean(Y)]
    C = np.tile(centroid,(X.size,1))
    # normalized, sorted distance
    D = np.sort(np.sqrt(np.sum((P - C) ** 2,axis=1)))

    # distances below the 90th percentile
    D90 = D[np.where(D < np.percentile(D,90))]
    D90 /= np.max(D90)

    i = np.linspace(0,1,D90.size)
    slope, intercept, rval, pval, stderr = stats.linregress(i,D90)

    return 1 - slope
