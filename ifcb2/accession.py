import re
import os
from datetime import datetime

from sqlalchemy import and_, or_, not_, desc, func, cast, Numeric

from oii.utils import sha1_file
from oii.times import text2utcdatetime
from oii.ifcb2 import get_resolver, HDR, ADC, ROI, HDR_PATH, ADC_PATH, ROI_PATH
from oii.ifcb2.identifiers import parse_pid
from oii.ifcb2.orm import Bin, File

from oii.ifcb2.formats.hdr import parse_hdr_file, TEMPERATURE, HUMIDITY

ACCESSION_ROLE='accession'

def compute_fixity(fs, fast=False):
    """fs - fileset"""
    paths = [fs[HDR_PATH], fs[ADC_PATH], fs[ROI_PATH]]
    filetypes = [HDR,ADC,ROI]
    for path,filetype in zip(paths,filetypes):
        f = File(local_path=path, filetype=filetype)
        f.compute_fixity(fast=fast)
        yield f

def compute_bin_metrics(fs, b):
    """fs - fileset, b - bin"""
    # hdr - temp / humidity
    hdr_path = fs[HDR_PATH]
    parsed_hdr = parse_hdr_file(hdr_path)
    b.humidity = parsed_hdr.get(HUMIDITY)
    b.temperature = parsed_hdr.get(TEMPERATURE)
    # adc - triggers, duration
    adc_path = fs[ADC_PATH]
    line = None
    with open(adc_path) as adc:
        for line in adc:
            pass
    if line is not None:
        triggers, seconds = re.split(r',',line)[:2]
        b.triggers = int(triggers)
        b.duration = float(seconds)

def fast_accession(session, ts_label, root):
    """accession without checksumming or integrity checks"""
    raw_filesets = get_resolver().ifcb.files.list_raw_filesets(root)
    n_total = 0
    n_new = 0
    for fs in raw_filesets:
        lid = fs['lid']
        try:
            parsed = parse_pid(lid)
        except:
            raise
        existing_bin = session.query(Bin).filter(and_(Bin.lid==lid,Bin.ts_label==ts_label)).first()
        n_total += 1
        if existing_bin:
            continue
        n_new += 1
        if n_new % 1000 == 0: # periodically commit
            session.commit()
        ts = text2utcdatetime(parsed['timestamp'], parsed['timestamp_format'])
        b = Bin(ts_label=ts_label, lid=lid, sample_time=ts)
        # now make fixity entries
        for f in compute_fixity(fs, fast=True):
            session.add(f)
            b.files.append(f)
        # now compute bin metrics
        try:
            compute_bin_metrics(fs, b)
        except:
            pass # FIXME warn
        session.add(b)
    session.commit()
    return (n_new, n_total)
