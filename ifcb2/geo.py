import sys
import pytz

import pandas as pd

from oii.ifcb2.session import session
from oii.ifcb2.feed import Feed

from oii.ifcb2.vehicle.cruise import TrackBins

def load_track_csv(csv_in):
    # fixme deal with detecting headings or lack of headings
    track = pd.read_csv(csv_in)
    track.index = pd.to_datetime(track.pop(track.columns[0]))
    track.index = track.index.tz_localize(pytz.utc)
    return track

class GeoFeed(Feed):
    def merge_track(self, track):
        begin = track.index.min()
        end = track.index.max()

        lids = []
        times = []

        bins = {}

        for b in self.time_range(begin, end):
            bins[b.lid] = b
            lids.append(b.lid)
            times.append(b.sample_time)

        bin_times = pd.DataFrame({'lid':lids},index=times)

        tb = TrackBins('',track,load=False)
        tb.bins = bin_times

        bins_track = tb.bins_track()

        for i in range(len(bins_track)):
            row = bins_track.iloc[i]
            lid = row['lid']
            lat = row['latitude']
            lon = row['longitude']
            b = bins[lid]
            b.lat = lat
            b.lon = lon

        self.session.commit()
    def clear_track(self):
        for b in self.time_range(): # all bins
            b.lat = None
            b.lon = None
        self.session.commit()
    def track2multipoint(self, begin=None, end=None):
        pts = []
        for b in self.time_range(begin, end):
            if b.lon is not None and b.lat is not None:
                pts.append('{:.6f} {:.6f}'.format(b.lon, b.lat))
        wkt = 'MULTIPOINT({})'.format(','.join(pts))
        return wkt
