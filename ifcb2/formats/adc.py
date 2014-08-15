from oii.ldr import Resolver
from oii.utils import search_path

p = search_path('oii/ifcb2/resolvers/ifcb.xml')
R = Resolver(p)

get_targets = R.as_function('ifcb.adc.get_targets')
get_target = R.as_function('ifcb.adc.get_target')

class Adc(object):
    def __init__(self, adc_file, schema_version='v2'):
        self.adc_file = adc_file
        self.schema_version = schema_version
    def get_targets(self):
        return get_targets(adc_file=self.adc_file, schema_version=self.schema_version)
    def get_target(self, targetNumber=1):
        try:
            return list(get_target(adc_file=self.adc_file, schema_version=self.schema_version, target=targetNumber))[0]
        except IndexError:
            return None

