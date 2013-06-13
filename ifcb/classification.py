from scipy.io import loadmat

def class_scores_mat2dicts(matfile, bin_lid):
    """Convert a class score .mat file into dicts"""
    mat = loadmat(matfile)

    scores = mat['TBscores'] # score matrix (roi x scores)
    labels = mat['class2useTB'] # class labels
    roinum = mat['roinum'] # roi num for each row

    label_strs = [l.astype(str)[0] for l in labels[:,0]]

    for roi, row in zip(roinum[:,0], scores[:]):
        d = dict(zip(label_strs,row.tolist()))
        d['pid'] = '%s_%05d' % (bin_lid, roi)
        yield d

def class_scores_mat2class_labels(matfile, bin_lid, threshold=0.0):
    for d in class_scores_mat2dicts(matfile, bin_lid):
        roi_lid = d['pid']
        del d['pid']
        v=list(d.values())
        k=list(d.keys())
        m=max(v)
        if m > threshold:
            yield roi_lid, k[v.index(m)]
        else:
            yield roi_lid, 'other' # not sure what to call this?

        
