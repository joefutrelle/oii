import time
import sys
from datetime import timedelta

import requests

from oii.ldr import Resolver

resolver_xml = """
<namespace name="wf">
  <rule name="pid" uses="pid" distinct="pid lid product extension">
    <var name="reid">[a-zA-Z][a-zA-Z0-9]*</var>
    <match var="pid" pattern="([^_.]+)(?:_(${reid}))?(?:\.(${reid}))?"
	   groups="lid product extension"/>
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
requests.get(api('/create/%s' % pid)) # raw is available
#p_lids = list(R.wf.products(pid))
#for p_lid in [s['product'] for s in p_lids]:
#    requests.post(api('/create/%s' % p_lid),data=dict(state='waiting'))

for dep in R.wf.deps(pid):
    dp, up, r = dep['product'], dep['upstream_product'], dep['role']
    form = dict(upstream=up, role=r)
    requests.post(api('/depend/%s' % dp),data=form)

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
            form = dict(state='available',event='completed')
            requests.post(api('/update/%s' % pid),data=form)
            print 'Completed %s' % pid
            return True

print 'starting work'

while do_work():
    print 'looking for more work'

print 'done working'
