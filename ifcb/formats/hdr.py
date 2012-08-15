import re

# hdr attributes. these are camel-case, mapped to column names below
TEMPERATURE = 'temperature'
HUMIDITY = 'humidity'
BINARIZE_THRESHOLD = 'binarizeThreshold'
SCATTERING_PMT_SETTING = 'scatteringPhotomultiplierSetting'
FLUORESCENCE_PMT_SETTING = 'fluorescencePhotomultiplierSetting'
BLOB_SIZE_THRESHOLD = 'blobSizeThreshold' 

# column name / type pairs
HDR_SCHEMA = [(TEMPERATURE, float),
              (HUMIDITY, float),
              (BINARIZE_THRESHOLD, int),
              (SCATTERING_PMT_SETTING, float),
              (FLUORESCENCE_PMT_SETTING, float),
              (BLOB_SIZE_THRESHOLD, int)]
# hdr column names
HDR_COLUMNS = ['Temp', 'Humidity', 'BinarizeThresh', 'PMT1hv(ssc)', 'PMT2hv(chl)', 'BlobSizeThresh']

CONTEXT = 'context'

def read_hdr(source):
    """Read header data from a source (see ifcb.io.Source)"""
    with source as hdr:
        return parse_hdr(hdr.readlines())

def parse_hdr(lines):
    """Given the lines of a header file, return the properties"""
    lines = [line.rstrip() for line in lines]
    props = {}
    if lines[0] == 'Imaging FlowCytobot Acquisition Software version 2.0; May 2010':
        props = { CONTEXT: [lines[0]] } # FIXME parse
    elif re.match(r'^softwareVersion:',lines[0]):
        props = { CONTEXT: [lines[0]] } # FIXME parse
    else:
        # "context" is what the text on lines 2-4 is called in the header file
        props = { CONTEXT: [lines[n].strip('"') for n in range(3)] }
        # now handle format variants
        if len(lines) >= 6: # don't fail on original header format
            columns = re.split(' +',re.sub('"','',lines[4])) # columns of metadata in CSV format
            values = re.split(' +',re.sub(r'[",]',' ',lines[5]).strip()) # values of those columns in CSV format
            # for each column take the string and cast it to the schema's column type
            for (column, (name, cast), value) in zip(HDR_COLUMNS, HDR_SCHEMA, values):
                props[name] = cast(value)
    return props
