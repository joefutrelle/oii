import os
import re
from datetime import timedelta, datetime
from glob import glob

import pandas as pd
import numpy as np

import pytz

from oii.utils import imemoize

@np.vectorize
def add_seconds(dt, s):
    return dt + timedelta(seconds=s)

# run time offsets from init time measured by T Crockford
OFFSET_NO_DEBUBBLE = 35
OFFSET_DEBUBBLE = 182

# other timing offsets as measured by T Crockford
# sample uptake time per ml
UPTAKE_TIME_ML = 10
# valve turn time (average)
VALVE_TURN_TIME = 6

# header and ADC column keys
SAMPLE_TIME = 'sampleTime'
RUN_TIME='runTime'
SCHEMA = 'ADCFileFormat'
DEBUBBLE = 'debubbleWithSample'
TRIGGER_TIME = 'ADC_time' # proxy for trigger time
ROI_X = 'ROIx'
ROI_Y = 'ROIy'
TIME_UTC = 'TimeUTC'

"""
assuming continuous sampling, here are the timings for two consecutive bins

|bin 1 time (init)  |~10s sample uptake |~6s valve turn |run start         |bin 2 time (init)
+-------------------+-------------------+---------------+------------------+----------------
  maybe debubble                                        {     run time     }
  maybe refill

(sample uptake time is approximately 10s per ml sampled)
if sampling is not continuous, syringe number will be reinitialized in second file
in that case, or if there is no following bin, check debubble flag in header
(and just believe it) and offset by the appropriate trigger time offset measured above
"""

class AdcTime(object):
    def __init__(self, adc_path, time_offset=None, next_bin=None, continuous=True):
        """adc path. time_offset, if left unspecified,
        will be computed by searching for the next bin
        in the same directory--unless "continuous" is False
        it's ok if path is missing extension.
        time_offset is the number of seconds between init time
        and start of sample uptake"""
        dr, name = os.path.split(adc_path)
        lid, ext = os.path.splitext(name)
        self.lid = lid
        self.adc_path = os.path.join(dr, lid + '.adc')
        self.hdr_path = os.path.join(dr, lid + '.hdr')
        self.next_bin = next_bin
        self.continuous = continuous
        if continuous and next_bin is None:
            # try to find next bin
            self.next_bin = self.find_next_bin(dr)
    @property
    @imemoize
    def headers(self):
        """parse HDR file ignoring non-RFC822 compliant lines"""
        headers = {}
        with open(self.hdr_path) as hdr:
            for line in hdr.readlines():
                line = line.rstrip()
                m = re.match('^([^:]+): (.*)$',line)
                if m is not None:
                    key, value = m.groups()
                    headers[key] = value
        return headers
    @property
    @imemoize
    def init_time(self):
        """return the UTC init timestamp from the headers"""
        timestamp = self.headers[SAMPLE_TIME] # init time is called "sample time" in headers
        return datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
    @property
    @imemoize
    def run_time(self):
        """get the run time of the sample. this is a duration in seconds"""
        return float(self.headers[RUN_TIME])
    @property
    @imemoize
    def sample_volume(self):
        """sample volume in ml"""
        return 1. # FIXME read from header field
    @property
    @imemoize
    def uptake_time(self):
        """return sample uptake time based on sample volume.
        this is a duration in seconds"""
        return self.sample_volume * UPTAKE_TIME_ML
    @property
    @imemoize
    def sample_time(self):
        """UTC timestamp of when sample uptake starts"""
        return self.init_time + timedelta(seconds=self.time_offset)
    @property
    @imemoize
    def schema(self):
        """return the ADC column names as a list"""
        return re.split(', ',self.headers[SCHEMA])
    def find_next_bin(self, dr):
        """find the ADC path of the next bin in the same directory
        as this one. if none is found, return None"""
        adc_paths = sorted(glob(os.path.join(dr,'*.adc')))
        try:
            ix = adc_paths.index(self.adc_path)
        except ValueError:
            return None
        try:
            return adc_paths[ix+1]
        except IndexError:
            return None
    @property
    @imemoize
    def time_offset(self):
        """next_bin should be the path of the subsequent bin,
        or an AdcTime object wrapping it.
        if no next bin is specified, use the debubble flag
        to select one of the measured offsets."""
        if self.next_bin is not None:
            try:
                next_init_time = self.next_bin.init_time
            except AttributeError: # duck type
                next_init_time = AdcTime(self.next_bin).init_time
            # compute interval between bin timestamps
            interval = next_init_time - self.init_time
            # now subtract run time and uptake / valve time
            adjusted_run_time = self.run_time + VALVE_TURN_TIME + self.uptake_time
            return interval.total_seconds() - adjusted_run_time
        else: # no next bin, use debubble flag
            if self.headers[DEBUBBLE] == '1': # may not be true. believe it
                return OFFSET_DEBUBBLE
            else:
                return OFFSET_NO_DEBUBBLE
    @property
    @imemoize
    def data(self):
        """read the adc data and add a 'TimeUTC' column"""
        adc = pd.read_csv(self.adc_path, header=None)
        adc.columns = self.schema
        adc[TIME_UTC] = add_seconds(self.sample_time, adc[TRIGGER_TIME])
        return adc
    @imemoize
    def roi_pos_binned(self, freq='10s'):
        grouper = pd.Grouper(key=TIME_UTC, freq=freq)
        cols = [ROI_X, ROI_Y]
        return self.data.groupby(grouper).mean()[cols]

def adc_time_series(data_dir):
    """given a data dir, return a DataFrame indexed by UTC sample time
    containing a row with bin LIDs"""
    adcs = glob(os.path.join(data_dir,'*.adc'))
    def rows():
        for adc, next_adc in zip(adcs, adcs[1:] + [None]):
            a = AdcTime(adc, next_bin=next_adc)
            yield {'lid':a.lid, 'sample_time':a.sample_time}
    df = pd.DataFrame(list(rows()))
    df.index = df.pop('sample_time')
    return df
