from jinja2 import FileSystemLoader, Template, Environment
from oii.config import parse_conf, get_subconf, list_subconfs

e = Environment(loader=FileSystemLoader('.'))
t = e.get_template('rtempl.j2')

config_file = 'rtempl.conf'

schema = dict(raw='list',blob='list',feature='list')

confs = parse_conf(config_file,schema=schema)
time_series = list_subconfs(confs)

c = {'time_series': time_series, 'tsconf': {}}
c = dict(c.items() + get_subconf(confs,None).items())

for ts in time_series:
    c['tsconf'][ts] = get_subconf(confs,ts)

print c
print t.render(c)


