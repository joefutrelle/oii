from oii.ifcb2 import get_resolver

TARGET_NUMBER='targetNumber'

class Adc(object):
    def __init__(self, adc_file, schema_version='v2'):
        self.adc_file = adc_file
        self.schema_version = schema_version
    def get_targets(self):
        gts_fn = get_resolver().as_function('ifcb.adc.get_targets')
        return gts_fn(adc_file=self.adc_file, schema_version=self.schema_version)
    def get_target(self, targetNumber=1):
        gt_fn = get_resolver().as_function('ifcb.adc.get_target')
        return next(gt_fn(adc_file=self.adc_file, schema_version=self.schema_version, target=targetNumber),None)

