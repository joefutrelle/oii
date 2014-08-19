from oii.csvio import csv_str, csv_quote
from oii.ifcb2.formats.adc import TARGET_NUMBER

def targets2csv(targets,schema_cols,headers=True):
    """Given targets, produce a CSV representation in the specified schema;
    targets should have had binID and pid added to them (see oii.ifcb2.identifiers)"""
    ks = schema_cols + ['binID','pid','stitched','targetNumber']
    if headers:
        yield ','.join(ks)
    for target in targets:
        # fetch all the data for this row as strings, emit
        yield ','.join(csv_quote(csv_str(target[k])) for k in ks)
