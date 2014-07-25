from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime, event
from sqlalchemy.orm import mapper

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
               Column('checksum_type', String))

def fixity_utc_listener(target, context):
    target.fix_time = dt2utcdt(target.fix_time)
    target.create_time = dt2utcdt(target.create_time)
    target.mod_time = dt2utcdt(target.mod_time)

mapper(Fixity, fixity)
event.listen(Fixity, 'load', fixity_utc_listener)

product = Table('products', metadata,
                Column('pid', String, primary_key=True),
                Column('status', String),
                Column('event', String),
                Column('ts', DateTime(timezone=True)))

def product_utc_listener(target, context):
    target.ts = dt2utcdt(target.ts)

mapper(Product, product)
event.listen(Product, 'load', product_utc_listener)

