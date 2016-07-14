from datetime import datetime

import pytz
import numpy as np
import pandas as pd
from scipy.io import loadmat
import requests

from oii.ifcb2.vehicle.kml import track2kml, bins2kml
from oii.ifcb2 import PID, TS_LABEL
from oii.utils import imemoize
from oii.times import ISO_8601_FORMAT

YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, LAT, LON = 'year','month','day','hour','minute','second','latitude','longitude'
DATE_COLS = [YEAR, MONTH, DAY, HOUR, MINUTE, SECOND]
COLS = DATE_COLS + [LAT, LON]

class CruiseTrack(object):
    """parse a cruise track. the assumption is that the cruise track is a .mat file
    containing the following variables (and possibly other ones, which will be ignored)
    'year','month','day','hour','minute','second','latitude','longitude'
    times must be UTC
    the resulting dataframe is available via the track property
    """
    def __init__(self, path, load=True):
        if load:
            self.load(path)
    def load(self, path):
        md = loadmat(path, squeeze_me=True)
        for key in md.keys(): # remove irrelevant keys
            if key not in COLS:
                del md[key]
        df = pd.DataFrame.from_dict(md)
        # convert date/time columns to UTC datetimes
        def row2datetime(row):
            return datetime(*[int(row[c]) for c in DATE_COLS], tzinfo=pytz.UTC)
        # make those datetimes the index
        df.index = df.apply(row2datetime, axis=1)
        self.track = df[[LAT, LON]]
    def track2kml(self, kml_path, title=None):
        df = self.track
        if title is None:
            title = 'Cruise track'
        track2kml(df.index, df[LAT], df[LON], kml_path, title=title)

class TrackBins(object):
    # take a track and find min and max times
    # query web services or Feed ORM API over that time range to get time for each bin
    # need to know namespace (http://{server}/{ts_label})
    # merge with cruise track using fillna approach to get bin lat/lon
    # produce dataframe suitable for kml rendering using kml.bins2kml
    """track must be a dataframe indexed by UTC datetime with columns
    'latitude' and 'longitude' e.g., what you get from CruiseTrack.track
    or Px4.lat_lon_binned()"""
    def __init__(self, namespace, track, load=True):
        self.namespace = namespace
        self.track = track
        if load:
            self.load()
    def load(self):
        """query the feed for the timestamped bins, in the cruise track
        date range"""
        ix = self.track.index
        start = ix.min().strftime(ISO_8601_FORMAT)
        end = ix.max().strftime(ISO_8601_FORMAT)
        metric = 'temperature' # this will be ignored
        ep = self.namespace.rstrip('/') + '/api/feed/%s/start/%s/end/%s' % (metric, start, end)
        json = requests.get(ep).json()
        feed = pd.DataFrame(json)
        feed.pop(metric) # don't care about the metric
        feed.index = feed.pop('date') # do not combine with next line
        feed.index = pd.to_datetime(feed.index, utc=True)
        self.bins = feed
    @imemoize
    def bins_track(self):
        """merge feed bins with cruise track using most recent cruise track
        coordinates for each bin"""
        merged = self.bins.merge(self.track, how='outer', left_index=True, right_index=True)
        for col in [LAT, LON]:
            merged[col].fillna(method='ffill', inplace=True) # forward fill lat/lon
        # remaining nas are for track points with no bin associated, drop them
        merged.dropna(inplace=True)
        return merged
    def bins2kml(self, kml_path, c=None, title=None):
        bt = self.bins_track()
        bins2kml(bt, kml_path, c=c, title=title)
