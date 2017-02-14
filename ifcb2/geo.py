import sys
import pytz

import pandas as pd

from oii.ifcb2.session import session
from oii.ifcb2.feed import Feed

from oii.ifcb2.vehicle.cruise import TrackBins

def load_track_csv(csv_in):
    track = pd.read_csv(csv_in)
    # test number of columns
    if len(track.columns) != 3:
        raise ValueError('CSV must have three columns: time, latitude, and longitude')
    # test for missing column headers
    try:
        # if the column name is a float, that's a data row
        float(track.columns[1])
        try:
            # if this is ssekable, seek to 0
            csv_in.seek(0)
        except AttributeError:
            # otherwise assume it's reopenable
            pass
        # reparse the CSV with no header row
        track = pd.read_csv(csv_in, header=None)
    except ValueError:
        # we got good column headers
        pass
    # FIXME check to see if lat/lon are switched
    track.columns = ['time','latitude','longitude']
    # parse UTC times and make into index
    track.index = pd.to_datetime(track.pop('time'))
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
