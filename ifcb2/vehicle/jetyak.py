import numpy as np
import pandas as pd

from scipy.io import loadmat

from oii.utils import imemoize
from oii.ifcb2.gps_time import gps2utc

# column names
TIME_UTC='TimeUTC' # UTC timestamp
TIME_US='TimeUS' # relative time in microseconds
ROLL='Roll' # vehicle roll
PITCH='Pitch' # vehicle pitch
LINE_NO='LineNo' # line number column
GPS_MS='GMS' # GPS week second in milliseconds
GPS_WEEK='GWk' # GPS week

# table names
GPS_TABLE='GPS' # GPS table (includes GPS_MS/GPS_WEEK and TIME_US)
TELEMETRY_TABLE='AHR2' # table with TIME_US, lat/lon, ROLL, PITCH, and yaw

class Px4(object):
    """represents a px4 logfile in mat format"""
    def __init__(self, path, load=True):
        self.path = path
        if load:
            self.load()
    def load(self, path=None):
        if path is None:
            path = self.path
        self.px4 = loadmat(path, squeeze_me=True)
    @imemoize
    def get_table(self, name):
        """get a table by name as a dataframe.
        assumes the first column is called 'LineNo' and pops that
        and uses it as a data index. Looks for a table called {name}_label
        and attempts to use that as column names"""
        data = self.px4[name]
        try:
            labels = self.px4[name + '_label']
        except KeyError:
            labels = None
        df = pd.DataFrame(data, index=data[:,0], columns=labels)
        df.pop(LINE_NO)
        return df
    @imemoize
    def get_epoch_gps(self):
        """determine what TimeUS=0 (and therefore Time in s = 0)
        is in GPS time.
        returns second-of-week and week"""
        gps = self.get_table(GPS_TABLE)
        # get row with first nonzero GMS
        gms = gps[GPS_MS] # GPS milliseconds column
        init = gps.loc[gms != 0].iloc[0] # first nonzero value
        time_s = init[TIME_US] / 1000000. # convert TimeUS ms to s
        gps_s = init[GPS_MS] / 1000. # convert GMS ms to s
        gps_week = init[GPS_WEEK]
        gps_time_s_offset = gps_s - time_s
        return gps_time_s_offset, gps_week
    @imemoize
    def get_utc_table(self, name):
        """get a named table with a TimeUS column and
        add a "TimeUTC" column with UTC time"""
        table = self.get_table(name)
        v_gps2utc = np.vectorize(gps2utc)
        gps_offset_s, gps_week = self.get_epoch_gps()
        gps_s = table[TIME_US] / 1000000. + gps_offset_s
        table[TIME_UTC] = pd.Series(v_gps2utc(gps_s, gps_week), index=table.index)
        return table
    @property
    @imemoize
    def telemetry(self):
        return self.get_utc_table('AHR2')
    @property
    @imemoize
    def roll_pitch_binned(self, freq='10s'):
        grouper = pd.Grouper(key=TIME_UTC, freq=freq)
        cols = [ROLL, PITCH]
        return self.telemetry.groupby(grouper).mean()[cols]
