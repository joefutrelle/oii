import re
import os
from datetime import datetime

from sqlalchemy import and_, or_, not_, desc, func, cast, Numeric

from oii.utils import sha1_file
from oii.times import text2utcdatetime
from oii.ifcb2 import get_resolver, HDR, ADC, ROI, HDR_PATH, ADC_PATH, ROI_PATH, LID
from oii.ifcb2.identifiers import parse_pid, get_timestamp
from oii.ifcb2.orm import Bin, File

from oii.ifcb2.formats.hdr import parse_hdr_file, TEMPERATURE, HUMIDITY

FIXITY_ROLE='fixity'
ACCESSION_ROLE='accession'

def compute_fixity(fs, fast=False):
    """fs - fileset"""
    paths = [fs[HDR_PATH], fs[ADC_PATH], fs[ROI_PATH]]
    filetypes = [HDR,ADC,ROI]
    for path,filetype in zip(paths,filetypes):
        f = File(local_path=path, filetype=filetype)
        f.compute_fixity(fast=fast)
        yield f

def compute_bin_metrics(b, fs):
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

def list_filesets(root):
    return get_resolver().ifcb.files.list_raw_filesets(root)

class Accession(object):
    def __init__(self,session,ts_label,fast=False):
        """session = IFCB ORM session"""
        self.session = session
        self.ts_label = ts_label
        self.fast = fast
    def bin_exists(self,lid):
        if self.session.query(Bin).filter(and_(Bin.lid==lid,Bin.ts_label==self.ts_label)).first():
            return True
        return False
    def new_bin(self,lid):
        parsed = parse_pid(lid)
        sample_time = get_timestamp(parsed)
        return Bin(ts_label=self.ts_label, lid=lid, sample_time=sample_time)
    def integrity(self,fileset):
        """stub"""
        return True
    def compute_fixity(self,b,fileset):
        """b = Bin instance,
        fileset = fileset structure"""
        # now make fixity entries
        for f in compute_fixity(fileset, fast=self.fast):
            b.files.append(f)
    def do_accession(self, root):
        n_total = 0
        n_new = 0
        for fileset in list_filesets(root):
            lid = fileset[LID] # get LID from fileset
            n_total += 1
            if self.bin_exists(lid): # make sure it doesn't exist
                continue
            if n_new % 1000 == 0: # periodically commit
                session.commit()
            b = self.new_bin(lid) # create new bin
            # now compute fixity
            self.compute_fixity(b,fileset)
            # now compute bin metrics
            try:
                self.compute_bin_metrics(b,fileset)
            except:
                pass # FIXME warn
            session.add(b)
        session.commit()
        return (n_total, n_new)
