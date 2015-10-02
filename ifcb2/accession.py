import re
import os
from datetime import datetime

import logging

from sqlalchemy import and_, or_, not_, desc, func, cast, Numeric

from oii.utils import sha1_file
from oii.times import text2utcdatetime
from oii.ifcb2 import get_resolver, HDR, ADC, ROI, HDR_PATH, ADC_PATH, ROI_PATH, LID, SCHEMA_VERSION
from oii.ifcb2.formats.integrity import check_fileset
from oii.ifcb2.identifiers import parse_pid, get_timestamp
from oii.ifcb2.orm import Bin, File, TimeSeries

from oii.ifcb2.formats.hdr import parse_hdr_file, TEMPERATURE, HUMIDITY

EXISTS='EXISTS'
ADDED='ADDED'
FAILED='FAILED'

def compute_fixity(fs, fast=False):
    """fs - fileset"""
    paths = [fs[HDR_PATH], fs[ADC_PATH], fs[ROI_PATH]]
    filetypes = [HDR,ADC,ROI]
    for path,filetype in zip(paths,filetypes):
        f = File(local_path=path, filetype=filetype)
        f.compute_fixity(fast=fast)
        logging.warn('FIXITY for %s: length=%d, checksum(sha1)=%s' % (path, f.length, f.sha1))
        yield f

def compute_bin_metrics(b, fs):
    """fs - fileset, b - bin"""
    # hdr - temp / humidity
    try:
        hdr_path = fs[HDR_PATH]
        parsed_hdr = parse_hdr_file(hdr_path)
        b.humidity = parsed_hdr.get(HUMIDITY)
        b.temperature = parsed_hdr.get(TEMPERATURE)
    except:
        logging.warn('METRICS FAILED to parse temperature / humidity')
    # adc - triggers, duration
    try:
        adc_path = fs[ADC_PATH]
        line = None
        with open(adc_path) as adc:
            for line in adc:
                pass
        if line is not None:
            triggers, seconds = re.split(r',',line)[:2]
            b.triggers = int(triggers)
            b.duration = float(seconds)
    except:
        logging.warn('METRICS FAILED to compute trigger rate')
    logging.warn('METRICS for %s: humidity=%.2f, temp=%.2fC, triggers=%d, duration=%.2fs' %\
                 (b.lid, b.humidity, b.temperature, b.triggers, b.duration))

def list_filesets(root):
    return get_resolver().ifcb.files.list_raw_filesets(root)

class Accession(object):
    def __init__(self,session,ts_label,fast=True):
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
    def test_integrity(self,b):
        parsed = parse_pid(b.lid)
        schema_version = parsed[SCHEMA_VERSION]
        fs = {}
        for f in b.files:
            fs[f.filetype] = f.local_path
        try:
            check_fileset(fs, schema_version)
            return True
        except:
            return False
    def compute_fixity(self,b,fileset):
        """b = Bin instance,
        fileset = fileset structure"""
        # now make fixity entries
        for f in compute_fixity(fileset, fast=self.fast):
            b.files.append(f)
    def get_time_series(self):
        return self.session.query(TimeSeries).filter(and_(TimeSeries.label==self.ts_label,TimeSeries.enabled)).first()
    def get_raw_roots(self):
        ts = self.get_time_series()
        if ts is None:
            return
        for dd in ts.data_dirs:
            if dd.product_type == 'raw':
                yield dd.path
    def accepts_products(self, product_type):
        ts = self.get_time_series()
        if ts is None:
            return False
        for dd in ts.data_dirs:
            if dd.product_type == product_type:
                return True
        return False
    def list_filesets(self,root=None):
        if root is not None:
            ddpaths = [root]
        else:
            ddpaths = self.get_raw_roots()
        for ddpath in ddpaths:
            for fs in list_filesets(ddpath):
                yield fs
    def add_fileset(self,fileset):
        """run one bin fileset through accession process. does not commit,
        returns 
        ADDED - if fileset was added
        EXISTS - if fileset exists
        FAILED - if accession failed"""
        lid = fileset[LID] # get LID from fileset
        if self.bin_exists(lid): # make sure it doesn't exist
            logging.warn('SKIP %s - exists' % lid)
            return EXISTS
        b = self.new_bin(lid) # create new bin
        # now compute fixity
        logging.warn('FIXITY computing fixity for %s' % lid)
        self.compute_fixity(b,fileset)
        # now test integrity
        if not self.test_integrity(b):
            logging.warn('FAIL %s - failed integrity checks' % lid)
            return FAILED
        logging.warn('PASS %s - integrity checks passed' % lid)
        # now compute bin metrics
        logging.warn('METRICS computing metrics for %s' % lid)
        try:
            compute_bin_metrics(b,fileset)
        except:
            logging.warn('METRICS FAIL computing metrics')
        logging.warn('ADDED %s to %s' % (lid, self.ts_label))
        self.session.add(b)
        return ADDED
    def add_all_filesets(self):
        n_total, n_new = 0, 0
        for fileset in self.list_filesets():
            n_total += 1
            if self.add_fileset(fileset):
                n_new +=1
            else:
                continue
            if n_new % 5 == 0: # periodically commit
                logging.warn('COMMITTING')
                self.session.commit()
        self.session.commit()
        return n_total, n_new
