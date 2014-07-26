from sqlalchemy import event
from sqlalchemy.types import DateTime
from sqlalchemy.orm.properties import ColumnProperty

from oii.times import dt2utcdt

def utc_datetime_attribute_instrument_listener(cls, key, inst):
    # here I'm assuming "key" is the class's attribute name - unclear from SQLAlchemy docs
    if isinstance(inst.property, ColumnProperty) and isinstance(inst.property.columns[0].type, DateTime):
        # listen for userland set operation and set timezone to UTC
        def setter(target, value, oldvalue, _):
            return dt2utcdt(value)
        event.listen(inst.property, 'set', setter, retval=True)
        # trigger a userland set operation
        def upset(target, *_):
            setattr(target, key, getattr(target, key))
        # do this on relevant instance events
        for event_type in ['init', 'load', 'refresh']:
            event.listen(cls, event_type, upset)

def fix_utc(cls):
    event.listen(cls, 'attribute_instrument', utc_datetime_attribute_instrument_listener)

