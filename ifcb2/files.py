from oii.ifcb2 import get_resolver
from oii.ifcb2.identifiers import parse_pid

from oii.ldr import pprint

def pid2file(pid):
    parsed_pid = parse_pid(pid)
    for r in get_resolver().ifcb.local.data_roots():
        root = r['root']
        for f in get_resolver().ifcb.files.find_raw_fileset(root=root,**parsed_pid):
            print f

import sys
if __name__=='__main__':
    pid2file(sys.argv[1])
