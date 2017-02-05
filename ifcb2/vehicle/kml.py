import numpy as np
import pandas as pd
from jinja2.environment import Template

from oii.times import ISO_8601_FORMAT
from oii.ifcb2 import PID

LAT='latitude'
LON='longitude'

KML_TRACK_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
 xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
  <name>{{title}}</name>
  <Placemark>
    <gx:Track>{% for ts in ts_iter %}
      <when>{{ts}}</when>{% endfor %}{% for lat, lon in ll_iter %}
      <gx:coord>{{lon}} {{lat}} 0</gx:coord>{% endfor %}
    </gx:Track>
  </Placemark>
</Document>
</kml>
"""

def track2kml(df, kml_path, title=None):
    """df must be a pandas dataframe indexed by UTC time with
    columns 'latitude' and 'longitude'"""
    if title is None:
        title = 'Vehicle track'
    def fmt_date(ts):
        try:
            return ts.to_datetime().strftime(ISO_8601_FORMAT)
        except AttributeError: # ducktype Python datetimes
            return ts.strftime(ISO_8601_FORMAT)
    ll_rows = df[[LAT, LON]].iterrows()
    context = {
        'title': title,
        'ts_iter': (fmt_date(ts) for ts in df.index),
        'll_iter': (row for _, row in ll_rows)
    }
    Template(KML_TRACK_TEMPLATE).stream(**context).dump(kml_path)

# diamond
DEFAULT_PLACEMARK_ICON='http://www.gstatic.com/mapspro/images/stock/962-wht-diamond-blank.png'

KML_PLACEMARK_TEMPLATE="""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{{title}}</name>{% if not color %}
  <Style id="redstyle">
    <IconStyle>
      <color>ff0000ff</color><!-- red -->
      <scale>0.5</scale><!-- smallish -->
      <Icon><href>{{icon}}</href></Icon>
    </IconStyle>
  </Style>{% endif %}{% for row in row_iter %}
  <Placemark>
    <name>{{row['lid']}}</name>{% if row['color'] %}
    <Style>
      <IconStyle>
        <color>{{row['color']}}</color>
        <scale>0.5</scale>
        <Icon><href>{{icon}}</href></Icon>
      </IconStyle>
    </Style>{% else %}
    <styleUrl>#redstyle</styleUrl>{% endif %}
    <TimeStamp>
      <when>{{row['date']}}</when>
    </TimeStamp>
    <Point>
      <coordinates>{{row['longitude']}},{{row['latitude']}},0</coordinates>
    </Point>
    <description><![CDATA[<a href="{{row['pid']}}.html">{{row['lid']}}</a>]]></description>
  </Placemark>{% endfor %}
</Document>
</kml>
"""

def bins2kml(df, kml_path, c=None, title=None):
    """df must be a pandas dataframe indexed by UTC datetime with
    the following columns:
    pid: the bin pid (no extension)
    latitude: decimal latitude
    longitude: decimal longitude
    in addition a column name bearing colors can be specified with the c keyword,
    it must contain abgr hex codes"""
    if title is None:
        title = 'IFCB runs'
    f = df.copy()
    f['lid'] = df[PID].str.replace(r'.*/','')
    def row_iter():
        color = None
        for ix, cols in f.iterrows():
            if c is not None:
                color = cols[c]
            row = {
                'date': ix.strftime(ISO_8601_FORMAT),
                'latitude': cols['latitude'],
                'longitude': cols['longitude'],
                'lid': cols['lid'],
                'pid': cols['pid'],
                'color': color
            }
            yield row
    context = {
        'row_iter': row_iter(),
        'title': title,
        'color': c,
        'icon': DEFAULT_PLACEMARK_ICON
    }
    Template(KML_PLACEMARK_TEMPLATE).stream(**context).dump(kml_path)
