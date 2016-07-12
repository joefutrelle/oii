import numpy as np
import pandas as pd
from jinja2.environment import Template

from oii.times import ISO_8601_FORMAT

KML_TRACK_TEMPLATE = """
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
 xmlns:gx="http://www.google.com/kml/ext/2.2">
<Folder>
  <Placemark>
    <gx:Track>{% for ts in ts_iter %}
      <when>{{ts}}</when>{% endfor %}{% for lat, lon in ll_iter %}
      <gx:coord>{{lon}} {{lat}} 0</gx:coord>{% endfor %}
    </gx:Track>
  </Placemark>
</Folder>
</kml>
"""

def track2kml(datetimes, lats, lons, kml_path):
    """lats, lons, and datetimes should be arrays or Pandas Series
    lat/lon must be decimal. datetime should either be a Python datetime object
    or a string in ISO8601 UTC format (YYYYMMDDTHHMMSSZ)"""
    def fmt_date(ts):
        return ts.to_datetime().strftime(ISO_8601_FORMAT)
    timestamps = pd.Series(np.array(datetimes))
    ll_rows = pd.DataFrame([lats, lons]).T.iterrows()
    context = {
        'ts_iter': (fmt_date(ts) for ts in timestamps),
        'll_iter': (row for _, row in ll_rows)
    }
    Template(KML_TRACK_TEMPLATE).stream(**context).dump(kml_path)
