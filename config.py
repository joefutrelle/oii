import re

class Configuration(object):
    """Arbitrary holder of configuration values"""
    pass

def parse_conf(pathname,schema=None):
    current_subconf = None
    confs = {None:{}}
    with open(pathname,'r') as configfile:
        for line in configfile:
            line = line.strip()
            if re.match('^#',line): # comment
                continue
            try:
                current_subconf = re.match(r'^\[(.*)\]',line).groups(0)[0].strip()
                confs[current_subconf] = {}
            except:
                pass
            try:
                (key, value) = re.match(r'^([^=]+)=(.*)',line).groups()
                key = key.strip()
                value = value.strip()
                try:
                    val_type = schema[key]
                    if val_type == 'list':
                        value = re.split(r'\s*,\s*',value)
                    elif val_type == 'bool':
                        value = value == 'True'
                    elif val_type == 'int':
                        value = int(value)
                except:
                    pass
                confs[current_subconf][key] = value
            except:
                pass
        return confs

def list_subconfs(confs):
    return [k for k in confs.keys() if k is not None]

def get_subconf(confs,subconf_name):
    return dict(confs[None].items() + confs[subconf_name].items())

def configure(obj,pathname,subconf_name=None,schema=None):
    confs = parse_conf(pathname)
    conf = get_subconf(confs,subconf_name)
    for k,v in conf.items():
        setattr(obj,k,v)
    return obj

def get_config(pathname,subconf_name=None,schema=None):
    return configure(Configuration(),pathname,subconf_name,schema)
