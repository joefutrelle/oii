from datetime import datetime
from math import floor
import re

import numpy as np
import requests
import pytz
from jdcal import jd2gcal

from oii.utils import memoize

GPS_EPOCH_JULIAN = 2444244.5 # the GPS epoch as a Julian date
GPS_CYCLE_WEEKS = 1024 # number of weeks in a GPS cycle
DAY_S = 86400. # number of seconds in a day
UTC_TAI_OFFSET = 19 # offset between TAI and UTC
MJD_EPOCH_JULIAN = 2400000.5 # MJD epoch as a Julian date

# leap seconds as of 24 June 2016
# used if offline
OFFLINE_LEAPSECONDS =  [
    (2457204.5, 36),
    (2456109.5, 35),
    (2454832.5, 34),
    (2453736.5, 33),
    (2451179.5, 32),
    (2450630.5, 31),
    (2450083.5, 30),
    (2449534.5, 29),
    (2449169.5, 28),
    (2448804.5, 27),
    (2448257.5, 26),
    (2447892.5, 25),
    (2447161.5, 24),
    (2446247.5, 23),
    (2445516.5, 22),
    (2445151.5, 21),
    (2444786.5, 20),
    (2444239.5, 19),
    (2443874.5, 18),
    (2443509.5, 17),
    (2443144.5, 16),
    (2442778.5, 15),
    (2442413.5, 14),
    (2442048.5, 13),
    (2441683.5, 12),
    (2441499.5, 11),
    (2441317.5, 10)
]

def gps2julian(timeOfWeek, week, cycle=0):
    """Convert GPS time to Julian date"""
    """Works for array-like objects"""
    week += cycle * GPS_CYCLE_WEEKS
    days = week * 7. + timeOfWeek / DAY_S + 0.5
    return GPS_EPOCH_JULIAN + days - 0.5

@memoize
def get_ls_jd():
    """Returns a list of 2-tuples where each is
    1. The Julian date of a leap second
    2. The offset between UTC and TAI following that leap second
    Tuples are returned in order of most recent first
    """
    url='https://www.ietf.org/timezones/data/leap-seconds.list'

    try:
        r = requests.get(url, stream=True, timeout=1)
        r.raise_for_status()
    except:
        return OFFLINE_LEAPSECONDS

    out = []
    
    for line in r.iter_lines():
        if line[0] == '#':
            continue
        # "ntp_time" is seconds since the NTP epoch
        # "tai_offset" is the offset between TAI and UTC starting at that time
        (ntp_time, tai_offset) = [int(d) for d in re.match(r'(\d+)\s+(\d+).*',line).groups()]
        # convert ntp time to julian date
        mjd = ntp_time / 86400. + 15020 # modified julian date
        jd = mjd + MJD_EPOCH_JULIAN # julian date
        out.append((jd, tai_offset))

    return out[::-1]

def get_gps_utc_offset(jd, ls_jd=None):
    """Get the GPS/UTC offset at a given Julian date"""
    if ls_jd is None:
        ls_jd = get_ls_jd()
    for ls, tai_offset in ls_jd:
        if jd > ls:
            return tai_offset - UTC_TAI_OFFSET
    # time is proleptic
    return 0 # not sure this is correct behavior

def gps2utc(timeOfWeek, week, cycle=0):
    """Convert GPS time to UTC, taking into account leap seconds"""
    week += cycle * GPS_CYCLE_WEEKS

    jd = gps2julian(timeOfWeek, week)

    leap_seconds_since_gps_epoch = get_gps_utc_offset(jd)
    offset = -1. * leap_seconds_since_gps_epoch / DAY_S

    year, month, day, daytime = jd2gcal(jd + offset, 0)

    day_seconds = daytime * DAY_S
    hours = int(day_seconds // 3600)
    minutes = int((day_seconds % 3600) // 60)
    frac_seconds = day_seconds % 60
    seconds = int(floor(frac_seconds))
    microseconds = int(floor(frac_seconds % 1 * 1000000))

    dt = datetime(year, month, day, hours, minutes, seconds, microseconds, pytz.utc)

    return dt


