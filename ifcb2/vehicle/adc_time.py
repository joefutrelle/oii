import os
import re
from datetime import timedelta, datetime

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
SCHEMA = 'ADCFileFormat'
DEBUBBLE = 'debubbleWithSample'
TRIGGER_TIME = 'ADC_time' # proxy for trigger time
ROI_X = 'ROIx'
ROI_Y = 'ROIy'
TIME_UTC = 'TimeUTC'

class AdcTime(object):
    def __init__(self, adc_path):
        """it's ok if path is missing extension"""
        dr, name = os.path.split(adc_path)
        name, ext = os.path.splitext(name)
        self.adc_path = os.path.join(dr, name + '.adc')
        self.hdr_path = os.path.join(dr, name + '.hdr')
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
        timestamp = self.headers[SAMPLE_TIME]
        return datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.UTC)
    @property
    @imemoize
    def schema(self):
        """return the ADC column names as a list"""
        return re.split(', ',self.headers[SCHEMA])
    @property
    @imemoize
    def data(self):
        """read the adc data and add a 'TimeUTC' column"""
        adc = pd.read_csv(self.adc_path, header=None)
        adc.columns = self.schema
        if self.headers[DEBUBBLE] == '1':
            offset = OFFSET_DEBUBBLE
        else:
            offset = OFFSET_NO_DEBUBBLE
        adc[TIME_UTC] = add_seconds(self.sample_time, offset + adc[TRIGGER_TIME])
        return adc

def roi_pos_binned(adc, freq='10s'):
    grouper = pd.Grouper(key=TIME_UTC, freq=freq)
    cols = [ROI_X, ROI_Y]
    return adc.data.groupby(grouper).mean()[cols]

    
        
        
