import csv

from sqlalchemy import and_

from oii.ifcb2 import LID
from oii.ifcb2.orm import Bin

LAT='lat'
LON='lon'
DEPTH='depth'

DATE='date'

class Geo(object):
    def __init__(self, session, ts_label=None):
        self.session = session
        self.ts_label = ts_label
    def _commit(self, commit):
        if not commit:
            return
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
    def add_track(self, track, commit=True):
        """track is [{ lid, lat, lon, depth }]
        where any key may be missing or None except lid"""
        for loc in track:
            lid = loc[LID]
            lat = loc.get(LAT)
            lon = loc.get(LON)
            depth = loc.get(DEPTH)
            b = self.session.query(Bin).\
                filter(Bin.ts_label==self.ts_label).\
                filter(Bin.lid==lid).first()
            if b is not None:
                b.lat = lat
                b.lon = lon
                b.depth = depth
        self._commit(commit)
    def get_track(self):
        q = self.session.query(Bin.lid, Bin.sample_time, Bin.lat, Bin.lon, Bin.depth).\
            filter(Bin.ts_label==self.ts_label).\
            filter(and_(Bin.lat.isnot(None), Bin.lon.isnot(None)))
        track = [dict(zip([LID,DATE,LAT,LON,DEPTH],row)) for row in q]
        return track
    def get_wkt(self):
        """get track in WKT format"""
        ps = ['%.6f %.6f' % (p[LON], p[LAT]) for p in self.get_track()]
        return 'LINESTRING(%s)' % ','.join(ps)
    def import_track(self, path):
        with open(path) as csvfile:
            fieldnames = [LID, LAT, LON, DEPTH]
            dr = csv.DictReader(csvfile, fieldnames)
            track = [d for d in dr]
        self.add_track(track)
