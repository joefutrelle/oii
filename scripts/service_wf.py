import time
import sys
from datetime import timedelta

import requests

from oii.ldr import Resolver

resolver_xml = """
<namespace name="wf">
  <rule name="pid" uses="pid" distinct="pid lid product extension">
    <var name="reid">[a-zA-Z][a-zA-Z0-9]*</var>
    <match var="pid" pattern="([^_.]+)(_(${reid}))?(.(${reid}))?"
	   groups="lid - product - extension"/>
  </rule>
  <rule name="deps" uses="pid" distinct="pid product upstream_product role">
    <invoke rule="wf.pid" using="pid" distinct="pid lid"/>
    <vars names="product upstream_product role" delim=",">
      <vals>${lid}_gray,${pid},color</vals>
      <vals>${lid}_canny,${lid}_gray,gray</vals>
      <vals>${lid}_final,${lid}_canny,overlay</vals>
      <vals>${lid}_final,${pid},background</vals>
    </vars>
  </rule>
  <rule name="products" uses="pid" distinct="product">
    <invoke rule="wf.deps" using="pid" distinct="product"/>
  </rule>
</namespace>
"""
R = Resolver(resolver_xml)

pid='blz:fnork:foo_raw.jpg'

BASE_URL = 'http://localhost:8080'

def api(url):
    return BASE_URL + url

P = {}
requests.get(api('/create/available/%s' % pid))
p_lids = list(R.wf.products(pid))
for p_lid in [s['product'] for s in p_lids]:
    requests.get(api('/create/waiting/%s' % p_lid))

for dep in R.wf.deps(pid):
    dp, up, r = dep['product'], dep['upstream_product'], dep['role']
    requests.get(api('/depend/%s/on/%s/as/%s' % (dp, up, r)))

def do_work():
    for worker_roles in [['color'], ['gray'], ['overlay','background']]:
        roles_arg = '/'.join(worker_roles)
        r = requests.get(api('/start_next/%s' % roles_arg))
        if r.status_code == 200:
            d = r.json()
            pid = d['pid']
            state = d['state']
            time.sleep(1)
            #print 'allowing stuff to expire'
            #Products(session).expire(timedelta(seconds=2))
            print 'Product %s in state %s' % (pid, state)
            requests.get(api('/changed/%s/%s/%s' % ('complete', 'available', pid)))
            print 'Completed %s' % pid
            return True

print 'starting work'

while do_work():
    print 'looking for more work'

print 'done working'
