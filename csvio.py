import csv

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
            
