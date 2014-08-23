import re
from oii.ifcb2 import get_resolver
from oii.utils import memoize

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
    schema = dict(zip(re.split(' ',hit['columns']),re.split(' ',hit['types'])))
    return schema

class Adc(object):
    def __init__(self, adc_file, schema_version='v2'):
        self.adc_file = adc_file
        self.schema_version = schema_version
        self.schema = get_schema(schema_version)
    def _cast_target(self,target):
        """modifies target in place"""
        for k,v in target.items():
            try:
                target[k] = _TYPE_CONV[self.schema[k]](v)
            except KeyError:
                pass
        return target
    def get_targets(self):
        gts_fn = get_resolver().ifcb.adc.get_targets
        for target in gts_fn(adc_file=self.adc_file, schema_version=self.schema_version):
            yield self._cast_target(target)
    def get_target(self, targetNumber=1):
        gt_fn = get_resolver().ifcb.adc.get_target
        target = next(gt_fn(adc_file=self.adc_file, schema_version=self.schema_version, target=targetNumber),None)
        return self._cast_target(target)
