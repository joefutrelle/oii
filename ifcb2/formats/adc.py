import re
from oii.ifcb2 import get_resolver
from oii.utils import memoize
from oii.csvio import read_csv, NO_LIMIT
from oii.iopipes import LocalFileSource

SCHEMA_VERSION_1 = 'v1'
SCHEMA_VERSION_2 = 'v2'

TARGET_NUMBER='targetNumber'
TRIGGER = 'trigger'
# location of ROI in camera field in pixels
BOTTOM = 'bottom'
LEFT = 'left'
# ROI extent in pixels
HEIGHT = 'height'
WIDTH = 'width'
# ROI byte offset
BYTE_OFFSET = 'byteOffset'

_TYPE_CONV = {
    'int': int,
    'float': float,
    'str': str
}

@memoize
def get_schema(schema_version):
    hit = next(get_resolver().ifcb.adc.schema(schema_version),None)
    def text2schema():
        for col,typ in zip(re.split(' ',hit['columns']),re.split(' ',hit['types'])):
            if typ in _TYPE_CONV:
                yield col,_TYPE_CONV[typ]
            else:
                yield col,str
    return list(text2schema())

def read_adc(adc_path, target_no=1, limit=-1, schema=None):
    """Convert ADC data in its native format to dictionaries representing each target.
    Read starting at the specified target number (default 1)"""
    target_number = target_no-1
    adc_source = LocalFileSource(adc_path)
    for row in read_csv(adc_source, schema, target_no-1, limit):
        target_number += 1
        # skip 0x0 targets
        if row[WIDTH] * row[HEIGHT] > 0:
            # add target number
            row[TARGET_NUMBER] = target_number
            yield row

def read_target(adc_path, target_no, schema=None):
    adc_source = LocalFileSource(adc_path)
    for target in read_adc(source, target_no, limit=1, schema_version=schema_version):
        return target
    raise KeyError('ADC data not found')

class Adc(object):
    def __init__(self, adc_file, schema_version=SCHEMA_VERSION_2):
        self.adc_file = adc_file
        self.schema_version = schema_version
        self.schema = get_schema(schema_version)
    def _cast_target(self, target):
        # cast target metadata field to schema-appropriate types
        for k,v in target.items():
            if k in self.schema:
                t = self.schema[k]
                if t in _TYPE_CONV:
                    target[k] = _TYPE_CONV[t](v)
        return target
    def get_targets(self, target=1, limit=NO_LIMIT):
        #gts_fn = get_resolver().ifcb.adc.get_targets
        #gts_fn(adc_file=self.adc_file, schema_version=self.schema_version)
        for target in read_adc(self.adc_file, target, limit, self.schema):
            yield self._cast_target(target)
    def get_target(self, targetNumber=1):
        #gt_fn = get_resolver().ifcb.adc.get_target
        #target = next(gt_fn(adc_file=self.adc_file, schema_version=self.schema_version, target=targetNumber),None)
        target = read_target(self.adc_file, target, self.schema)
        return self._cast_target(target)
    def get_some_targets(self, offset=1, limit=1):
        for target in self.get_targets(target=offset, limit=limit):
            yield self._cast_target(target)
