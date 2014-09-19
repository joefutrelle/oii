from oii.times import utcdtnow
from oii.orm_utils import fix_utc

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime, func, distinct
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.associationproxy import association_proxy

Base = declarative_base()

fix_utc(Base)

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    pid = Column('pid', String)
    state = Column('state', String, default='available')
    event = Column('event', String, default='new')
    message = Column('message', String)
    ts = Column('ts', DateTime(timezone=True), default=utcdtnow)

    depends_on = association_proxy('upstream_dependencies', 'upstream')
    dependents = association_proxy('downstream_dependencies', 'downstream')

    def changed(self, event, state='updated', message=None, ts=None):
        """call when the product's state changes."""
        self.event = event
        self.state = state
        self.message = message
        if ts is None:
            ts = utcdtnow()
        self.ts = ts

    def deps_for_role(self, role):
        return [ud.upstream for ud in self.upstream_dependencies if ud.role==role]

    def dep_for_role(self, role):
        try:
            return self.deps_for_role(role)[0]
        except IndexError:
            return None

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

    DEFAULT_ROLE='any'

    id = Column(Integer, primary_key=True)
    upstream_id = Column(String, ForeignKey('products.id'))
    downstream_id = Column(String, ForeignKey('products.id'))
    role = Column(String, default=DEFAULT_ROLE, nullable=False)

    upstream = relationship(Product,
                            primaryjoin=upstream_id==Product.id,
                            backref=backref('downstream_dependencies', cascade='all,delete-orphan'))
    downstream = relationship(Product,
                              primaryjoin=downstream_id==Product.id,
                              backref=backref('upstream_dependencies', cascade='all,delete-orphan'))

    # proxy for upstream product's state
    state = association_proxy('upstream', 'state')

    def __repr__(self):
        if self.role==Dependency.DEFAULT_ROLE:
            return '<%s depends on %s>' % (self.downstream, self.upstream)
        else:
            return '<%s depends on %s (as %s)>' % (self.downstream, self.role, self.upstream)

# queries that range across entire product dependency hierarchies
# requires that an SQLA session be passed into each call

class Products(object):
    def __init__(self, session):
        self.session = session
    def count(self):
        return self.session.query(Product).count()
    def add_dep(self, downstream, upstream, role=None):
        d = Dependency(downstream=downstream, upstream=upstream, role=role)
        self.session.add(d)
    def younger_than(self, ago):
        """find all products whose events occurred more recently than ago ago.
        ago must be a datetime.timedelta"""
        now = utcdtnow()
        return self.session.query(Product).\
            filter(Product.ts > now - ago)
    def older_than(self, ago):
        """find all products whose events occurred longer than ago ago.
        ago must be a datetime.timedelta"""
        now = utcdtnow()
        return self.session.query(Product).\
            filter(Product.ts < now - ago)
    def roots(self):
        """return all roots; that is, products with no dependencies"""
        return self.session.query(Product).filter(~Product.depends_on.any())
    def leaves(self):
        """return all leaves; that is, products with no dependents"""
        return self.session.query(Product).filter(~Product.dependents.any())
    def get_next(self, roles=[Dependency.DEFAULT_ROLE], state='waiting', dep_state='available'):
        """find any product that is in state state and whose upstream dependencies are all in
        dep_state and satisfy all the specified roles, and lock it for update"""
        return self.session.query(Product).\
            join(Product.upstream_dependencies).\
            filter(Product.state==state).\
            filter(Dependency.state==dep_state).\
            filter(Dependency.role.in_(roles)).\
            group_by(Product).\
            having(func.count(Dependency.role)==len(roles)).\
            having(func.count(distinct(Dependency.role))==len(set(roles))).\
            with_lockmode('update').\
            first()
    def delete_intermediate(self, state='available', dep_state='available'):
        """delete all products that
        - are in 'state'
        - have any dependencies (in other words, not "root" products")
        - have any dependents, all of which are in 'dep_state'
        default is to find available products that no unavailable products depend on"""
        for product in self.session.query(Product).\
            filter(Product.state==state).\
            filter(Product.depends_on.any()).\
            filter(Product.dependents.any()).\
            filter(~Product.dependents.any(Product.state!=dep_state)).\
            with_lockmode('update'):
            self.session.delete(product)
        self.session.commit()

