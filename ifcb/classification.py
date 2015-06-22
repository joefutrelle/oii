from scipy.io import loadmat

def load_class_scores(matfile):
    return loadmat(matfile)

def class_scores_labels(mat):
    labels = mat['class2useTB'] # class labels
    return [l.astype(str)[0] for l in labels[:,0]]

def class_scores_mat2dicts(mat):
    """Convert a class score mat structure into dicts"""
    scores = mat['TBscores'] # score matrix (roi x scores)
    roinum = mat['roinum'] # roi num for each row

    label_strs = class_scores_labels(mat)

    for roi, row in zip(roinum[:,0], scores[:]):
        d = dict(zip(label_strs,row.tolist()))
        d['roinum'] = int(roi)
        yield d

def max_interpretation(scores, threshold=0.0):
    """This intepretation chooses the class with the maximum score,
    as long as the score is over a given threshold. If no scores
    were over the threshold, returns -1"""
    m = max(scores)
    if m > threshold:
        return scores.index(m)
    else:
        return -1 # no scores were over the threshold

def class_scores_mat2class_labels(mat, threshold=0.0):
    for d in class_scores_mat2dicts(mat):
        roinum = d['roinum']
        del d['roinum']
        c = max_interpretation(list(d.values()))
        k = list(d.keys())
        if c == -1:
            yield roinum, 'unclassified'
        else:
            yield roinum, k[c]

def class_scores_mat2class_label_score(mat):
    """return roinum, class label and score of max scoring class per roi"""
    for d in class_scores_mat2dicts(mat):
        roinum = d['roinum']
        del d['roinum']
        scores = list(d.values())
        s = max(scores)
        c = scores.index(max(scores))
        k = list(d.keys())
        if c == -1:
            yield roinum, 'unclassified', s
        else:
            yield roinum, k[c], s

def class_scores_mat2class_numbers(mat, threshold=0.0):
    scores = mat['TBscores'] # score matrix (roi x scores)
    roinum = mat['roinum'] # roi num for each row

    label_strs = class_scores_labels(mat)

    max_roinum = roinum[-1,0]

    class_numbers = [0 for n in range(max_roinum+1)] # there has GOT to be a better way!

    for roi, row in zip(roinum[:,0], scores[:]):
        v = row.tolist()
        m=max(v)
        if m > threshold:
            class_numbers[roi] = v.index(m)
        else:
            class_numbers[roi] = -1  # not sure what to call this?

    return class_numbers
    
