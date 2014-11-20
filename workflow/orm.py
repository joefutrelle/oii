from oii.times import utcdtnow
from oii.orm_utils import fix_utc

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime, func, distinct, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.associationproxy import association_proxy

# keys for use in the database and webapi

PID='pid'

# state and states
STATE='state'
NEW_STATE='new_state'
WAITING='waiting'
RUNNING='running'
AVAILABLE='available'

# event and events
EVENT='event'
HEARTBEAT='heartbeat'

# message
MESSAGE='message'

# role and roles
ROLE='role'
ANY='any'

# dependencies
UPSTREAM='upstream'

# declarative SQLAlchemy ORM
Base = declarative_base()

# UTC timezone used throughout
fix_utc(Base)

class Product(Base):
    """Represents a data product, or proxy object representing a desired outcome,
    that is in some current state and is a node in a product dependency DAG.
    For example a file of processed data file derived from two input data files
    file: in that case there would be three products, and two dependency
    relationships between the output file and the two input files."""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True) # row ID
    pid = Column('pid', String, unique=True) # persistent ID of product
    state = Column('state', String, default=AVAILABLE) # current state
    event = Column('event', String, default='created') # most recent state transition event
    message = Column('message', String) # event log message
    ts = Column('ts', DateTime(timezone=True), default=utcdtnow) # time of event

    depends_on = association_proxy('upstream_dependencies', 'upstream')
    dependents = association_proxy('downstream_dependencies', 'downstream')

    def changed(self, event, state=RUNNING, message=HEARTBEAT, ts=None):
        """call to record the event of a product state change"""
        if event is not None:
            self.event = event
        if state is not None:
            self.state = state
        if message is not None:
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
    """Represents a depdenency between two products. The dependency is
    one-way (proceeds from "upstream" to "downstream") and is associated
    with a role identifying the type of relationship the dependency represents.
    For example a quotient depends upstream on a numerator and on a denominator.
    In this model products do not have explicit types, only dependencies have
    explicit roles."""
    __tablename__ = 'dependencies'

    id = Column(Integer, primary_key=True)
    upstream_id = Column(String, ForeignKey('products.id'))
    downstream_id = Column(String, ForeignKey('products.id'))
    role = Column(String, default=ANY, nullable=False)

    upstream = relationship(Product,
                            primaryjoin=upstream_id==Product.id,
                            backref=backref('downstream_dependencies', cascade='all,delete-orphan'))
    downstream = relationship(Product,
                              primaryjoin=downstream_id==Product.id,
                              backref=backref('upstream_dependencies', cascade='all,delete-orphan'))

    UniqueConstraint('upstream_id','downstream_id','role')

    # proxy for upstream product's state
    state = association_proxy('upstream', 'state')

    def __repr__(self):
        if self.role==ANY:
            return '<%s depends on %s>' % (self.downstream, self.upstream)
        else:
            return '<%s depends on %s (as %s)>' % (self.downstream, self.role, self.upstream)

# queries that range across entire product dependency hierarchies
# requires that an SQLA session be passed into each call

class Products(object):
    def __init__(self, session):
        self.session = session
    def commit(self):
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
    def get_product(self,pid,create=None):
        p = self.session.query(Product).filter(Product.pid==pid).first()
        if not p and create is not None:
            self.session.add(create)
            return create
        else:
            return p
    def count(self):
        return self.session.query(Product).count()
    def add_dep(self, downstream, upstream, role=None):
        d = Dependency(downstream=downstream, upstream=upstream, role=role)
        self.session.add(d)
        return self
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
    def _update_commit(self, product=None, event=None, new_state=None, message=None):
        if product is not None:
            product.changed(event, new_state, message)
            self.commit()
            return product
        else:
            return None
    def get_next(self, roles=[ANY], state=WAITING, dep_state=AVAILABLE):
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
    def start_next(self, roles=[ANY], state=WAITING, dep_state=AVAILABLE, new_state=RUNNING, event='start_next', message=None):
        """find any product that is in state state and whose upstream dependencies are all in
        dep_state and satisfy all the specified roles, atomically set it to the new state with
        the given event and message values. If no product is in the state queried, will return
        None instead"""
        p = self.get_next(roles, state, dep_state)
        return self._update_commit(p, event, new_state, message)
    def update_if(self, pid, state=WAITING, new_state=RUNNING, event='update_if', message=None):
        """atomically change the state of the given product, but only if it's
        in the specified current state"""
        p = self.session.query(Product).\
            filter(Product.state==state).\
            with_lockmode('update').\
            first()
        return self._update_commit(p, event, new_state, message)
    def delete_tree(self,pid):
        p = self.get_product(pid)
        if p is None:
            return self
        td = [p] + list(p.ancestors)
        for d in td:
            self.session.delete(d)
        return self
    def delete_intermediate(self, state=AVAILABLE, dep_state=AVAILABLE):
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
    def expire(self, ago, state=RUNNING, new_state=WAITING):
        """if a product has not had an event since ago ago (see older_than),
        and is in state, change its state to new_state"""
        if state == new_state:
            raise ValueError('state and new_state are both %s' % state)
        for p in self.older_than(ago).filter(Product.state==state):
            p.changed('expired', new_state)
        self.session.commit()