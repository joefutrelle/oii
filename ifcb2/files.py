from oii.ifcb2 import get_resolver
from oii.ifcb2.identifiers import parse_pid

from oii.ldr import pprint

class NotFound(Exception):
    pass

def pid2fileset(pid,roots):
    parsed_pid = parse_pid(pid)
    return parsed_pid2fileset(parsed_pid,roots)

def parsed_pid2fileset(parsed_pid,roots):
    paths = {}
    for root in roots:
        try:
            p = next(get_resolver().ifcb.files.find_raw_fileset(root=root,**parsed_pid))
            paths.update(p)
            if paths:
                return paths
        except StopIteration:
            pass # try the next one
    # we tried all roots and it's not there
    raise NotFound('No raw data found for %s' % parsed_pid['bin_lid'])

import sys
if __name__=='__main__':
    print pid2fileset(sys.argv[1],roots=['/mnt/data/okeanos'])
