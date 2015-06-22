import time
import sys
from datetime import timedelta

import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, distinct
from sqlalchemy.orm import sessionmaker

from oii.ldr import Resolver

from oii.workflow.product_orm import Base, Product, Dependency, Products

engine = sqlalchemy.create_engine('sqlite:///')
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

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

pid='foo_raw.jpg'

P = {}
P[pid] = Product(pid=pid,state='available')
p_lids = list(R.wf.products(pid))
for p_lid in [s['product'] for s in p_lids]:
    print p_lid
    P[p_lid] = Product(pid=p_lid, state='waiting')

session.add_all(P.values())

for dep in R.wf.deps(pid):
    Products(session).add_dep(P[dep['product']], P[dep['upstream_product']], dep['role'])

session.commit()

def do_work():
    for worker_roles in [['color'], ['gray'], ['overlay','background']]:
        p = Products(session).start_next(worker_roles)
        if p is not None:
            for wr in worker_roles:
                print 'using %s for %s' % (p.deps_for_role(wr), wr)
            time.sleep(1)
            print 'allowing stuff to expire'
            Products(session).expire(timedelta(seconds=2))
            print 'Product %s in state %s' % (p, p.state)
            p.changed('complete', 'available')
            session.commit()
            print 'Completed %s' % p
            return True
    return False

print 'starting work'

while do_work():
    print 'looking for more work'

print 'done working'
