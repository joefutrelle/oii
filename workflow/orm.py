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
                Column('status', String),
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

