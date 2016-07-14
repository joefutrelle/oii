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
    lat/lon must be decimal. datetime should either be a Python datetime object,
    or a Pandas Timestamp object,
    or a string in ISO8601 UTC format (YYYYMMDDTHHMMSSZ)"""
    def fmt_date(ts):
        try:
            return ts.to_datetime().strftime(ISO_8601_FORMAT)
        except AttributeError: # ducktype Python datetimes
            return ts.strftime(ISO_8601_FORMAT)
    timestamps = pd.Series(np.array(datetimes))
    ll_rows = pd.DataFrame([lats, lons]).T.iterrows()
    context = {
        'ts_iter': (fmt_date(ts) for ts in timestamps),
        'll_iter': (row for _, row in ll_rows)
    }
    Template(KML_TRACK_TEMPLATE).stream(**context).dump(kml_path)

KML_PLACEMARK_TEMPLATE="""
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>IFCB runs</name>{% for row in row_iter %}
  <Placemark>
    <name>{{row['pid']}}</name>
    <Style>
      <IconStyle>
        <color>{{row['color']}}</color>
        <scale>0.5</scale><!-- smallish -->
        <Icon>
          <href>http://www.gstatic.com/mapspro/images/stock/962-wht-diamond-blank.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <TimeStamp>
      <when>{{row['date']}}</when>
    </TimeStamp>
    <Point>
      <coordinates>{{row['longitude']}},{{row['latitude']}},0</coordinates>
    </Point>
    <description><![CDATA[<a href="{{row['pid']}}.html">{{row['pid']}}</a>]]></description>
  </Placemark>{% endfor %}
</Document>
</kml>
"""

def bins2kml(df, kml_path, c=None):
    """df must be a pandas dataframe indexed by UTC datetime with
    the following columns:
    pid: the bin pid (no extension)
    latitude: decimal latitude
    longitude: decimal longitude
    in addition a column name bearing colors can be specified with the c keyword,
    it must contain abgr hex codes"""
    def row_iter():
        color = 'ff0000ff'
        for ix, cols in df.iterrows():
            if c is not None:
                color = cols[c]
            row = {
                'date': ix.strftime(ISO_8601_FORMAT),
                'latitude': cols['latitude'],
                'longitude': cols['longitude'],
                'pid': cols['pid'],
                'color': color
            }
            yield row
    Template(KML_PLACEMARK_TEMPLATE).stream(row_iter=row_iter()).dump(kml_path)

