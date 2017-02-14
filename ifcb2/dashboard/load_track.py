import sys
import pytz

import pandas as pd

from oii.ifcb2.session import session
from oii.ifcb2.geo import GeoFeed, load_track_csv

if __name__=='__main__':
    ts_label = sys.argv[1]
    with GeoFeed(session, ts_label) as geo:
        if sys.argv[2] == 'clear':
            geo.clear_track()
        else:
            track_csv = sys.argv[2]
            track = load_track_csv(track_csv)
            geo.merge_track(track)
