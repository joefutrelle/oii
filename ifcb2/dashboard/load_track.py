import sys
import pytz

import pandas as pd

from oii.ifcb2.session import session
from oii.ifcb2.feed import Feed

from oii.ifcb2.vehicle.cruise import TrackBins

def load_track_csv(csv_path):
    track = pd.read_csv(csv_path)
    track.index = pd.to_datetime(track.pop(track.columns[0]))
    track.index = track.index.tz_localize(pytz.utc)
    return track

def merge_track(ts_label, track):
    begin = track.index.min()
    end = track.index.max()

    feed = Feed(session, ts_label)

    lids = []
    times = []
    
    bins = {}

    for b in feed.time_range(begin, end):
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

    session.commit()

if __name__=='__main__':
    ts_label = sys.argv[1]
    track_csv = sys.argv[2]
    track = load_track_csv(track_csv)
    merge_track(ts_label, track)
