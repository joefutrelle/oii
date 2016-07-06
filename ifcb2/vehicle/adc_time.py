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

# first trigger time offsets measured by T Crockford
OFFSET_NO_DEBUBBLE = 35
OFFSET_DEBUBBLE = 182

# header and ADC column keys
SAMPLE_TIME = 'sampleTime'
RUN_TIME='runTime'
SCHEMA = 'ADCFileFormat'
DEBUBBLE = 'debubbleWithSample'
TRIGGER_TIME = 'ADC_time' # proxy for trigger time
ROI_X = 'ROIx'
ROI_Y = 'ROIy'
TIME_UTC = 'TimeUTC'

class AdcTime(object):
    def __init__(self, adc_path, time_offset=None, next_bin=None, continuous=True):
        """adc path. time_offset, if left unspecified,
        will be computed by searching for the next bin
        in the same directory--unless "continuous" is False
        it's ok if path is missing extension"""
        dr, name = os.path.split(adc_path)
        name, ext = os.path.splitext(name)
        self.adc_path = os.path.join(dr, name + '.adc')
        self.hdr_path = os.path.join(dr, name + '.hdr')
        # figure out time offset
        self.time_offset = None
        if time_offset is not None:
            self.time_offset = time_offset
        elif continuous:
            if next_bin is not None:
                self.set_time_offset(next_bin)
            else:
                self.set_time_offset(self.find_next_bin(dr))
        else: # use debubble algo
            self.set_time_offset(None)
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
    def sample_time(self):
        """return the UTC sample time from the headers"""
        timestamp = self.headers[SAMPLE_TIME]
        return datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
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
    def set_time_offset(self, next_bin=None):
        """next_bin should be the path of the subsequent bin,
        or an AdcTime object wrapping it.
        if no next bin is specified, use the debubble flag
        to select one of the measured offsets.
        if time_offset has already been set, just return that."""
        if self.time_offset is not None:
            return self.time_offset
        if next_bin is not None:
            try:
                next_sample_time = next_bin.sample_time
            except AttributeError: # duck type
                next_sample_time = AdcTime(next_bin, time_offset=0).sample_time
            # compute interval between bin timestamps
            interval = next_sample_time - self.sample_time
            # now subtract run time
            self.time_offset = interval.total_seconds() - float(self.headers[RUN_TIME])
        else: # no next bin, use debubble flag
            if self.headers[DEBUBBLE] == '1':
                self.time_offset = OFFSET_DEBUBBLE
            else:
                self.time_offset = OFFSET_NO_DEBUBBLE
    @property
    @imemoize
    def data(self):
        """read the adc data and add a 'TimeUTC' column"""
        adc = pd.read_csv(self.adc_path, header=None)
        adc.columns = self.schema
        adc[TIME_UTC] = add_seconds(self.sample_time, self.time_offset + adc[TRIGGER_TIME])
        return adc
    @imemoize
    def roi_pos_binned(self, freq='10s'):
        grouper = pd.Grouper(key=TIME_UTC, freq=freq)
        cols = [ROI_X, ROI_Y]
        return self.data.groupby(grouper).mean()[cols]

    
        
        
