import numpy as np
import pandas as pd

from scipy.io import loadmat

from oii.utils import imemoize
from oii.times import ISO_8601_FORMAT
from oii.ifcb2.gps_time import gps2utc
from oii.ifcb2.vehicle.kml import track2kml
from oii.ifcb2.vehicle import trackutil as tu

# column names
TIME_UTC='TimeUTC' # UTC timestamp
TIME_US='TimeUS' # relative time in microseconds
ROLL='Roll' # vehicle roll
PITCH='Pitch' # vehicle pitch
LINE_NO='LineNo' # line number column
GPS_MS='GMS' # GPS week second in milliseconds
GPS_WEEK='GWk' # GPS week
LAT='Lat' # latitude
LON='Lng' # longitude

# table names
GPS_TABLE='GPS' # GPS table (includes GPS_MS/GPS_WEEK and TIME_US)
TELEMETRY_TABLE='AHR2' # table with TIME_US, lat/lon, ROLL, PITCH, and yaw

DEFAULT_FREQ='10s'

class Px4(object):
    """represents a px4 logfile in mat format"""
    def __init__(self, path, labels_from=None, load=True):
        self.path = path
        self.labels_from = labels_from
        if load:
            self.load()
    def load(self, path=None):
        if path is None:
            path = self.path
        self.px4 = loadmat(path, squeeze_me=True)
    @imemoize
    def get_table_columns(self, table_name):
        label_tname = table_name + '_label'
        labels = self.px4 # default
        if self.labels_from is not None:
            labels = loadmat(self.labels_from, variable_names=[label_tname], squeeze_me=True)
        return labels[label_tname]
    @imemoize
    def get_table(self, name):
        """get a table by name as a dataframe.
        assumes the first column is called 'LineNo' and pops that
        and uses it as a data index. Looks for a table called {name}_label
        and attempts to use that as column names"""
        data = self.px4[name]
        # if the following raises KeyError it is fatal because we have
        # no column labels
        columns = self.get_table_columns(name)
        df = pd.DataFrame(data, index=data[:,0], columns=columns)
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
        time_s = init[TIME_US] / 1000000. # convert TimeUS microseconds to s
        gps_s = init[GPS_MS] / 1000. # convert GMS ms to s
        gps_week = init[GPS_WEEK]
        gps_time_s_offset = gps_s - time_s
        return gps_time_s_offset, gps_week
    @imemoize
    def get_utc_table(self, name):
        """get a named table with a TimeUS column and
        index it by UTC time; this will replace the existing index"""
        table = self.get_table(name)
        v_gps2utc = np.vectorize(gps2utc)
        gps_offset_s, gps_week = self.get_epoch_gps()
        gps_s = table[TIME_US] / 1000000. + gps_offset_s
        #table[TIME_UTC] = pd.Series(v_gps2utc(gps_s, gps_week), index=table.index)
        table.index = v_gps2utc(gps_s, gps_week)
        return table
    @property
    @imemoize
    def telemetry(self):
        return self.get_utc_table(TELEMETRY_TABLE)
    @imemoize
    def roll_pitch_binned(self, freq=DEFAULT_FREQ):
        return tu.group_mean(self.telemetry, freq)[[ROLL, PITCH]]
    @imemoize
    def track(self, freq=DEFAULT_FREQ):
        track = tu.group_mean(self.telemetry, freq)[[LAT, LON]]
        track.columns = ['latitude', 'longitude']
        return track
    def track2kml(self, kml_path, freq=DEFAULT_FREQ, title=None):
        track = self.track(freq)
        track2kml(track, kml_path, title=title)
