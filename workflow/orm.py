from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime, event
from sqlalchemy.orm import mapper, relationship, backref
from sqlalchemy.ext.associationproxy import association_proxy

from oii.orm_utils import fix_utc

from oii.times import dt2utcdt

from oii.workflow.product import Product
from oii.workflow.fixity import Fixity

metadata = MetaData()

fixity = Table('fixity', metadata,
               Column('pid', String, primary_key=True),
               Column('pathname', String, primary_key=True),
               Column('length', BigInteger),
               Column('checksum', String, primary_key=True),
               Column('fix_time', DateTime(timezone=True)),
               Column('create_time', DateTime(timezone=True)),
               Column('mod_time', DateTime(timezone=True)),
               Column('checksum_type', String, primary_key=True))

fix_utc(Fixity)    
mapper(Fixity, fixity)

product = Table('products', metadata,
                Column('pid', String, primary_key=True),
                Column('state', String),
                Column('event', String),
                Column('ts', DateTime(timezone=True)))

product_deps = Table('product_deps', metadata,
                     Column('dependent', String, ForeignKey('products.pid')),
                     Column('depends_on', String, ForeignKey('products.pid')))

fix_utc(Product)
mapper(Product, product, properties={
        'depends_on': relationship(Product,
                                   secondary=product_deps,
                                   primaryjoin=product.c.pid==product_deps.c.dependent,
                                   secondaryjoin=product.c.pid==product_deps.c.depends_on,
                                   backref='dependents')
})

# queries that range across entire product dependency hierarchies
# requires that an SQLA session be passed into each call

class ProductSet(object):
    def count(self, session):
        return session.query(Product).count()
    def get_next(self, session, dep_state='available', old_state='waiting', new_state='running', new_event='start'):
        """find any product that is in state old_state and all of whose
        dependencies are in dep_state, and atomically set its state to new_state.
        default is to find any product which is waiting and all of whose dependencies are available
        and trigger a start->running event"""
        p = session.query(Product).\
            filter(Product.state==old_state).\
            filter(Product.depends_on.any(Product.state==dep_state)).\
            filter(~Product.depends_on.any(Product.state!=dep_state)).\
            with_lockmode('update').\
            first()
        if p is None:
            return None
        p.changed(new_event,new_state)
        session.commit()
        return p
    def delete_used(self, session, state='available', dep_state='available'):
        """delete all products in state all of whose dependents are in dep_state.
        default is to find available products that no unavailable products depend on"""
        for product in session.query(Product).\
            filter(Product.state==state).\
            filter(Product.dependents.any()).\
            filter(~Product.dependents.any(Product.state!=dep_state)).\
            with_lockmode('update'):
            product.depends_on = []
            product.dependents = []
            session.delete(product)
        session.commit()
