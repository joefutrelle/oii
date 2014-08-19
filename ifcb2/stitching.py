from oii.ifcb2.formats.adc import TRIGGER, LEFT, BOTTOM, WIDTH, HEIGHT

STITCHED='stitched'

def overlaps(t1, t2):
    if t1[TRIGGER] == t2[TRIGGER]:
        (x11, y11) = (t1[LEFT], t1[BOTTOM])
        (x12, y12) = (x11 + t1[WIDTH], y11 + t1[HEIGHT])
        (x21, y21) = (t2[LEFT], t2[BOTTOM])
        (x22, y22) = (x21 + t2[WIDTH], y21 + t2[HEIGHT])
        overlaps = x11 < x22 and x12 > x21 and y11 < y22 and y12 > y21
        return overlaps
    return False

def find_pairs(targets):
    prev = None
    for target in targets:
        if prev is not None and overlaps(target, prev):
            yield (prev, target)
        prev = target

def stitched_box(targets):
    # compute bounds relative to the camera field
    x = min([target[LEFT] for target in targets])
    y = min([target[BOTTOM] for target in targets])
    w = max([target[LEFT] + target[WIDTH] for target in targets]) - x
    h = max([target[BOTTOM] + target[HEIGHT] for target in targets]) - y
    return (x,y,w,h)

def list_stitched_targets(targets):
    """Adjust a list of targets for stitching"""
    # in the stitching case we need to compute "stitched" flags based on pairs
    # correct image metrics
    targets = list(targets) # consume any iterator
    Bs = []
    for a,b in find_pairs(targets):
        (a[LEFT], a[BOTTOM], a[WIDTH], a[HEIGHT]) = stitched_box([a,b])
        a[STITCHED] = 1
        b[STITCHED] = 0
        Bs.append(b)
    # exclude the second of each pair from the list of targets
    targets = filter(lambda target: target not in Bs, targets)
    for target in targets:
        if not STITCHED in target:
            target[STITCHED] = 0
    return targets
