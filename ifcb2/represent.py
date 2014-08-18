from oii.csvio import csv_str, csv_quote
from oii.ifcb2.formats.adc import TARGET_NUMBER

PID='pid'

def add_bin_pid(targets, bin_pid):
    for target in targets:
        # add a binID and pid what are the right keys for these?
        target['binID'] = '%s' % bin_pid
        target['pid'] = '%s_%05d' % (bin_pid, target[TARGET_NUMBER])
    return targets

def bin2csv(targets,schema_cols):
    """Given targets, produce a CSV representation in the specified schema"""
    ks = schema_cols + ['binID','pid','stitched','targetNumber']
    yield ','.join(ks)
    for target in targets:
        # FIXME fake it till you make it
        target['binID'] = 'placeholder'
        target['pid'] = 'placeholder'
        target['stitched'] = 'placeholder'
        # fetch all the data for this row as strings, emit
        yield ','.join(csv_quote(csv_str(target[k])) for k in ks)
