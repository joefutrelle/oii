"""Imaging FlowCytobot dashboard and related utilities, for dashboard v3"""
import os
from oii.utils import memoize, search_path
from oii import ldr
from oii.ldr import Resolver

IFCB_RESOLVER_BASE_PATH='oii/ifcb2/resolvers'

@memoize()
def locate_resolver(name):
    return search_path(os.path.join(IFCB_RESOLVER_BASE_PATH,name))
    
@memoize(ttl=30)
def get_resolver():
    return ldr.get_resolver(locate_resolver('ifcb.xml'))
