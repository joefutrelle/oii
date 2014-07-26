from sqlalchemy import event
from sqlalchemy.types import DateTime

from oii.times import dt2utcdt

def utc_datetime_attribute_instrument_listener(cls, key, inst):
    # here I'm assuming "key" is the class's attribute name - unclear from SQLAlchemy docs
    if isinstance(inst.property.columns[0].type, DateTime):
        def setter(target, value, oldvalue, _):
            return dt2utcdt(value)
        event.listen(inst.property, 'set', setter, retval=True)
        def loader(target, _):
            setattr(target, key, getattr(target, key))
        event.listen(cls, 'load', loader)

def fix_utc(cls):
    event.listen(cls, 'attribute_instrument', utc_datetime_attribute_instrument_listener)


