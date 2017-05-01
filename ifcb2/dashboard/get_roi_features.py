import re

def get_roi_features_json(feature_file_path, roi_number):
    with open(feature_file_path) as fin:
        header = True
        out = ''
        for line in fin.readlines():
            line = line.rstrip()
            if header:
                line = re.sub('^','"',line)
                line = re.sub(',','","',line)
                line = re.sub('$','"',line)
                out += r'{{"names":[{}],'.format(line)
                header = False
                continue
            rn = int(re.match(r'(\d+),.*',line).groups()[0])
            if rn == roi_number:
                out += '"values":[{}]}}'.format(line)
                break
    return out
