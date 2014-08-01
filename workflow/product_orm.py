from oii.times import utcdtnow
from oii.orm_utils import fix_utc

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

fix_utc(Base)

class Product(Base):
    __tablename__ = 'products'

    pid = Column('pid', String, primary_key=True)
    state = Column('state', String, default='available')
    event = Column('event', String, default='new')
    ts = Column('ts', DateTime(timezone=True), default=utcdtnow)

    @property
    def upstream_products(self):
        return [u.upstream for u in self.upstream_dependencies]

    @property
    def downstream_products(self):
        return [d.downstream for d in self.downstream_dependencies]

    @property
    def ancestors(self):
        for parent in self.upstream_products:
            yield parent
            for anc in parent.ancestors:
                yield anc

    @property
    def descendants(self):
        for child in self.downstream_products:
            yield child
            for desc in child.descendants:
                yield desc

    def __repr__(self):
        return '<Product %s (%s) @ %s>' % (self.pid, self.state, self.ts)

class Dependency(Base):
    __tablename__ = 'dependencies'

    upstream_id = Column(String, ForeignKey('products.pid'), primary_key=True)
    downstream_id = Column(String, ForeignKey('products.pid'), primary_key=True)
    role = Column(String)

    upstream = relationship(Product,
                            primaryjoin=upstream_id==Product.pid,
                            backref='upstream_dependencies')
    downstream = relationship(Product,
                              primaryjoin=downstream_id==Product.pid,
                              backref='downstream_dependencies')

    def __repr__(self):
        return '<Dependency %s -> %s>' % (self.upstream, self.downstream)

