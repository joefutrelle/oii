import re

class Configuration(object):
    """Arbitrary holder of configuration values"""
    pass

def configure(obj,pathname,subconf_name=None,schema=None):
    current_subconf = None
    with open(pathname,'r') as configfile:
        for line in configfile:
            line = line.strip()
            if re.match('^#',line): # comment
                continue
            try:
                current_subconf = re.match(r'^\[(.*)\]',line).groups(0)[0].strip()
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
                if current_subconf is None or current_subconf == subconf_name:
                    setattr(obj,key,value)
            except:
                pass
        return obj

def get_config(pathname,subconf_name=None,schema=None):
    return configure(Configuration(),pathname,subconf_name,schema)
    
