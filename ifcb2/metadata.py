import sys
import csv
import re
import tempfile

from zipfile import ZipFile, ZIP_DEFLATED
from StringIO import StringIO
import shutil

from tagging import Tagging
from oii.times import iso8601, text2utcdatetime

"""
External metadata associated with bins, including
- lat/lon/depth
- skip flags
- tags
"""

LID='bin'
TIME='time'
LAT='lat'
LON='lon'
DEPTH='depth'
SKIP='skip'
ADD_TAG='addtag'
REMOVE_TAG='removetag'
TAGS='tags'

SCHEMA=[LID, TIME, LAT, LON, DEPTH, SKIP, ADD_TAG, REMOVE_TAG, TAGS]

def write_metadata_zip(feed, fout=sys.stdout):
    with tempfile.SpooledTemporaryFile() as temp:
        z = ZipFile(temp,'w',ZIP_DEFLATED)
        for year in feed.years():
            print year
            yout = StringIO()
            write_metadata(feed, yout, year=year)
            name = '%s_%d_metadata.csv' % (feed.ts_label, year)
            z.writestr(name, yout.getvalue())
            yout.close()
        z.close()
        temp.seek(0)
        shutil.copyfileobj(temp, fout)

def write_metadata(feed, fout=sys.stdout, year=None):
    if year is None:
        q = feed.all()
    else:
        q = feed.year(year)
    writer = csv.DictWriter(fout, SCHEMA)
    writer.writeheader()
    for b in q:
        writer.writerow({
            LID: b.lid,
            TIME: iso8601(b.sample_time.timetuple()),
            LAT: b.lat,
            LON: b.lon,
            DEPTH: b.depth,
            SKIP: 'X' if b.skip else None,
            TAGS: ','.join(b.tags)
        })
         

def read_metadata(feed, fin=sys.stdin):
    tagging = Tagging(feed.session, feed.ts_label)
    def split_tag_field(tag_field):
        if not tag_field:
            return []
        return re.split(', *',tag_field)
    for row in csv.DictReader(fin):
        lid, time, lat, lon, depth, skip, add_tag, remove_tag, tags = [row.get(f) for f in SCHEMA]
        if not lid:
            raise IOError('malformed metadata, missing bin ID')
        b = feed.get_bin(lid)
        print 'for bin %s' % lid
        if time:
            dt = text2utcdatetime(time)
            if dt != b.sample_time:
                print 'set timestamp to %s' % time 
                b.sample_time = dt
        if lat and lon:
            lat, lon = float(lat), float(lon)
            if b.lat != lat and b.lon != lon:
                print 'set lat/lon to %f,%f' % (lat,lon)
                b.lat = lat
                b.lon = lon
        if depth:
            depth = float(depth)
            if b.depth != depth:
                print 'set depth to %f' % depth
                b.depth = float(depth)
        if skip and not b.skip:
            print 'set skip flag to True'
            b.skip = True
        elif not skip and b.skip:
            print 'set skip flag to False'
            b.skip = False
        if add_tag or tags:
            add_tags = split_tag_field(add_tag) + split_tag_field(tags)
            for tag in add_tags:
                print 'add tag %s' % tag
                tagging.add_tag(b, tag, commit=False)
        if remove_tag:
            remove_tags = split_tag_field(remove_tag)
            for tag in remove_tags:
                print 'remove tag %s' % tag
                tagging.remove_tag(b, tag, commit=False)
    try:
        feed.session.commit()
    except:
        # FIXME What to do?
        feed.session.rollback()
