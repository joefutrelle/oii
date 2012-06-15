from oii import resolver
import sys

if __name__=='__main__':
    (_, config, pid) = sys.argv
    r = resolver.parse(config)
    for (hit,bindings) in resolver.resolve(r, dict(pid=pid)):
        print hit
