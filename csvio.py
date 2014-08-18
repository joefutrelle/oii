import csv
import re

"""Utilities for reading and writing CSV. uses source/sink from io"""

def parse_csv_row(row, schema=None):
    if schema is None:
        return dict(zip(range(len(row)), row))
    else:
        return dict([(colname,cast(value)) for (colname,cast),value in zip(schema,row)])

def read_csv(source, schema=None, offset=0, limit=-1):
    with source as csvdata:
        for row in csv.reader(csvdata):
            if offset <= 0:
                if limit == 0:
                    return
                limit -= 1
                yield parse_csv_row(row,schema)
            else:
                offset -= 1

def csv_quote(thing):
    """For a given string that is to appear in CSV output, quote it if it is non-numeric"""
    if re.match(r'^-?[0-9]*(\.[0-9]+)?$',thing):
        return thing
    else:
        return '"' + thing + '"'

def csv_str(v,numeric_format='%.12f'):
    """For a given value, produce a CSV representation of it"""
    try:
        return re.sub(r'\.$','',(numeric_format % v).rstrip('0'))
    except:
        return str(v)
            
