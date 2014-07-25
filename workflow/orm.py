from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import mapper

from oii.workflow.fixity import Fixity

metadata = MetaData()

fixity = Table('fixity', metadata,
               Column('pid', String),
               Column('pathname', String, primary_key=True),
               Column('length', BigInteger),
               Column('checksum', String),
               Column('fix_time', DateTime(timezone=True), primary_key=True),
               Column('create_time', DateTime(timezone=True)),
               Column('mod_time', DateTime(timezone=True)),
               Column('checksum_type', String))

mapper(Fixity, fixity)
