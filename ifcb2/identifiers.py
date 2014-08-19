from oii.ifcb2 import get_resolver
from oii.ifcb2.formats.adc import TARGET_NUMBER

BIN_KEY='binID'
TARGET_KEY='pid'

class IdentifierSyntaxError(Exception):
    pass

def parse_pid(pid):
    """use the IFCB resolver to parse a pid"""
    try:
        return next(get_resolver().ifcb.pid(pid))
    except:
        raise IdentifierSyntaxError(pid)

def target_pid(bin_pid,target_number=1):
    """bin_pid must have no product or extension,
    but may have a namespace prefix"""
    return '%s_%05d' % (bin_pid, target_number)

def add_pids(targets,bin_pid,bin_key='binID',target_key='pid'):
    """bin_pid must have no product or extension,
    but may have a namespace prefix"""
    for target in targets:
        target[bin_key] = bin_pid
        target[target_key] = target_pid(bin_pid,target[TARGET_NUMBER])
        yield target
