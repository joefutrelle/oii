import os

from oii.utils import safe_copy, compare_files

from oii.ifcb2.orm import Base, Instrument, TimeSeries, DataDirectory
from oii.ifcb2 import get_resolver, ResolverError, HDR, ADC, ROI, PID
from oii.ifcb2.files import NotFound, pid2fileset
from oii.ifcb2.accession import ACCESSION_ROLE

WILD_PRODUCT='wild'
RAW_PRODUCT='raw'

def list_filesets(instrument):
    """list all filesets currently present in the data directory,
    and return the full pathname of each file as a tuple suitable
    for constructing a dictionary from, like this
    (LID, {
        HDR: {full path of header file}
        ADC: {full path of ADC file}
        ROI: {full path of ROI file}
    })"""
    # first figure out which file goes with which LID
    # and ignore files that aren't RAW data files
    sets = {}
    src_dir = instrument.data_path
    for fname in os.listdir(src_dir):
        (lid, pext) = os.path.splitext(fname)
        pext = pext[1:]
        if not pext in [HDR, ADC, ROI]:
            continue
        if not lid in sets:
            sets[lid] = {}
        sets[lid][pext] = os.path.join(src_dir, fname)
    # now yield all complete filesets
    for lid in sorted(sets,reverse=True):
        s = sets[lid]
        if HDR in s and ADC in s and ROI in s:
            yield (lid, s)

def get_copy_from(instrument):
    """Return all raw file copy operations as tuples of
    - src: source path in instrument data directory
    - dest: destination path according to time series data dir configuration."""
    # for each complete fileset in the instrument data directory,
    for lid,src_fs in list_filesets(instrument):
        # see if the fileset already exists in the time series data dirs
        try:
            fs = pid2fileset(lid, [dd.path for dd in instrument.time_series.data_dirs])
            continue # files exist, no need to copy
        except NotFound:
            pass # fall through
        # compute the destination path for each file in the time series destination dirs
        for dest_dir in instrument.time_series.destination_dirs:
            dest_dir_path = dest_dir.path
            # for each raw data file type
            for ext in [HDR, ADC, ROI]:
                pid = '%s.%s' % (lid, ext)
                for s in get_resolver().ifcb.files.raw_destination(pid=pid,root=dest_dir_path):
                    src_path = src_fs[ext]
                    dest_path = s['file_path']
                    yield (lid, src_path, dest_path)
                    break # only need one destination

def do_copy(instrument):
    for lid,src,dest in get_copy_from(instrument):
        # if necessary, safe-copy the file
        if not os.path.exists(dest):
            safe_copy(src,dest)
            compare_files(src,dest,size=True)
            yield (lid,src,dest)

def as_product(pid,product):
    return next(get_resolver().ifcb.as_product(pid=pid,product=product))[PID]

def schedule_accession(client,pid):
    """use a oii.workflow.WorkflowClient to schedule an accession job for a fileset.
    pid must not be a local id--it must be namspace-scoped"""
    upstream_pid = as_product(pid,WILD_PRODUCT)
    downstream_pid = as_product(pid,RAW_PRODUCT)
    client.depend(downstream_pid, upstream_pid, ACCESSION_ROLE)

def copy_work(instrument,client,callback=None):
    ts_label = instrument.time_series.label
    for lid, src, dest in do_copy(instrument):
        pid = '%s/%s' % (ts_label, lid)
        schedule_accession(client,pid)
        if callback is not None:
            callback(lid)
