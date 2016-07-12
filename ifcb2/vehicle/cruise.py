from datetime import datetime

import pytz
import numpy as np
import pandas as pd
from scipy.io import loadmat

from oii.ifcb2.vehicle.kml import track2kml

YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, LAT, LON = 'year','month','day','hour','minute','second','latitude','longitude'
DATE_COLS = [YEAR, MONTH, DAY, HOUR, MINUTE, SECOND]
COLS = DATE_COLS + [LAT, LON]

class CruiseTrack(object):
    """parse a cruise track. the assumption is that the cruise track is a .mat file
    containing the following variables (and possibly other ones, which will be ignored)
    'year','month','day','hour','minute','second','latitude','longitude'
    """
    def __init__(self, path):
        md = loadmat(path,squeeze_me=True)
        for key in md.keys(): # remove irrelevant keys
            if key not in COLS:
                del md[key]
        df = pd.DataFrame.from_dict(md)
        # convert date/time columns to UTC datetimes
        def row2datetime(row):
            return datetime(*[int(row[c]) for c in DATE_COLS], tzinfo=pytz.UTC)
        # make those datetimes the index
        df.index = df.apply(row2datetime, axis=1)
        self.track = df
    def track2kml(self, kml_path):
        df = self.track
        track2kml(df.index, df[LAT], df[LON], kml_path)



