from oii.times import utcdtnow
from oii.orm_utils import fix_utc

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.associationproxy import association_proxy

Base = declarative_base()

fix_utc(Base)

class Product(Base):
    __tablename__ = 'products'

    pid = Column('pid', String, primary_key=True)
    state = Column('state', String, default='available')
    event = Column('event', String, default='new')
    ts = Column('ts', DateTime(timezone=True), default=utcdtnow)

    depends_on = association_proxy('upstream_dependencies', 'upstream')
    dependents = association_proxy('downstream_dependencies', 'downstream')

    @property
    def ancestors(self):
        for parent in self.depends_on:
            yield parent
            for anc in parent.ancestors:
                yield anc

    @property
    def descendants(self):
        for child in self.dependents:
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
                            backref=backref('downstream_dependencies', cascade='all,delete-orphan'))
    downstream = relationship(Product,
                              primaryjoin=downstream_id==Product.pid,
                              backref=backref('upstream_dependencies', cascade='all,delete-orphan'))

    def __repr__(self):
        return '<Dependency %s depends on %s>' % (self.downstream, self.upstream)

# queries that range across entire product dependency hierarchies
# requires that an SQLA session be passed into each call

class Products(object):
    @staticmethod
    def count(session):
        return session.query(Product).count()
    @staticmethod
    def get_next(session, dep_state='available', old_state='waiting', new_state='running', new_event='start'):
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
        p.state=new_state
        p.event=new_event
        p.ts=utcdtnow()
        session.commit()
        return p
    @staticmethod
    def roots(session):
        """return all roots; that is, products with no dependencies"""
        return session.query(Product).filter(~Product.depends_on.any())
    @staticmethod
    def leaves(session):
        """return all leaves; that is, products with no dependents"""
        return session.query(Product).filter(~Product.dependents.any())
    @staticmethod
    def delete_intermediate(session, state='available', dep_state='available'):
        """delete all products that
        - are in 'state'
        - have any dependencies (in other words, not "root" products")
        - have any dependents, all of which are in 'dep_state'
        default is to find available products that no unavailable products depend on"""
        for product in session.query(Product).\
            filter(Product.state==state).\
            filter(Product.depends_on.any()).\
            filter(Product.dependents.any()).\
            filter(~Product.dependents.any(Product.state!=dep_state)).\
            with_lockmode('update'):
            session.delete(product)
        session.commit()
    @staticmethod
    def younger_than(session, ago):
        """find all products whose events occurred more recently than ago ago.
        ago must be a datetime.timedelta"""
        now = utcdtnow()
        return session.query(Product).\
            filter(Product.ts > now - ago)
    @staticmethod
    def older_than(session, ago):
        """find all products whose events occurred longer than ago ago.
        ago must be a datetime.timedelta"""
        now = utcdtnow()
        return session.query(Product).\
            filter(Product.ts < now - ago)

