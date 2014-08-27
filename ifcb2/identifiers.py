from time import strptime

from oii.ifcb2 import get_resolver
from oii.ifcb2.formats.adc import TARGET_NUMBER

PID='pid'
LID='lid'
ADC_COLS='adc_cols'
SCHEMA_VERSION='schema_version'
TIMESTAMP='timestamp'
TIMESTAMP_FORMAT='timestamp_format'

# keys used in target dicts
BIN_KEY='binID'
TARGET_KEY='pid'

class IdentifierSyntaxError(Exception):
    pass

def parse_pid(pid):
    """use the IFCB resolver to parse a pid"""
    try:
        return next(get_resolver().ifcb.pid(pid))
    except StopIteration:
        raise

def get_timestamp(parsed_pid):
    """extract the timestamp from a parsed pid"""
    return strptime(parsed_pid[TIMESTAMP], parsed_pid[TIMESTAMP_FORMAT])

def target_pid(bin_pid,target_number=1):
    """bin_pid must have no product or extension,
    but may have a namespace prefix"""
    return '%s_%05d' % (bin_pid, target_number)

def add_pid(target,bin_pid,bin_key='binID',target_key='pid'):
    target[bin_key] = bin_pid
    target[target_key] = target_pid(bin_pid,target[TARGET_NUMBER])
    return target

def add_pids(targets,bin_pid,bin_key='binID',target_key='pid'):
    """bin_pid must have no product or extension,
    but may have a namespace prefix"""
    for target in targets:
        yield add_pid(target,bin_pid,bin_key,target_key)

def canonicalize(base_url, ts_label, lid):
    return '%s%s/%s' % (base_url, ts_label, lid)
