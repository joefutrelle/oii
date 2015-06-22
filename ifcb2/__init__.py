"""Imaging FlowCytobot dashboard and related utilities, for dashboard v3"""
import os
from oii.utils import memoize, search_path
from oii import ldr
from oii.ldr import Resolver
from oii.ifcb2 import resolvers

# keys and constants
PID='pid'
LID='lid'
TS_LABEL='ts_label'

NAMESPACE='namespace'
BIN_LID='bin_lid'

SCHEMA_VERSION='schema_version'

HDR='hdr'
ADC='adc'
ROI='roi'
HDR_PATH='hdr_path'
ADC_PATH='adc_path'
ROI_PATH='roi_path'
RAW='raw'

FILE_PATH='file_path'

IFCB_RESOLVER_BASE_PATH='oii/ifcb2/resolvers'

class ResolverError(Exception):
    pass

@memoize()
def locate_resolver(name):
    #return search_path(os.path.join(IFCB_RESOLVER_BASE_PATH,name))
    for d in resolvers.__path__:
        cand = os.path.join(d,name)
        if os.path.exists(cand):
            return cand
    
@memoize(ttl=30)
def get_resolver():
    return ldr.get_resolver(locate_resolver('ifcb.xml'))
