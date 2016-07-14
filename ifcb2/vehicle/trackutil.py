import pandas as pd

"""utils for dealing with tracks
a track is a Pandas dataframe indexed by UTC datetime
with 'latitude' and 'longitude' columns that are
decimal lat/lons."""

def group_mean(track, freq):
    """group a track by datetime and compute mean
    of lat lon for each timestamp
    freq is a time frequency, allowable objects are described here
    http://pandas.pydata.org/pandas-docs/stable/timeseries.html
    they can be strings e.g., '10s'
    """
    grouper = pd.Grouper(freq=freq)
    return track.groupby(grouper).mean()
    
