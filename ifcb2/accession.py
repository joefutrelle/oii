import os
from datetime import datetime

from oii.times import text2utcdatetime
from oii.ifcb2 import get_resolver
from oii.ifcb2.identifiers import parse_pid
from oii.ifcb2.orm import Bin, File

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
        existing_bin = session.query(Bin).filter(Bin.lid==lid).first()
        n_total += 1
        if existing_bin:
            continue
        n_new += 1
        ts = text2utcdatetime(parsed['timestamp'], parsed['timestamp_format'])
        b = Bin(ts_label=ts_label, lid=lid, sample_time=ts)
        session.add(b)
        # now make fixity entries
        now = datetime.now()
        paths = [fs['hdr_path'], fs['adc_path'], fs['roi_path']]
        filetypes = ['hdr','adc','roi']
        for path,filetype in zip(paths,filetypes):
            length = os.stat(path).st_size
            name = os.path.basename(path)
            # skip checksumming, because it's slow
            #checksum = sha1_file(path)
            checksum = '(placeholder)'
            f = File(local_path=path, filename=name, length=length, filetype=filetype, sha1=checksum, fix_time=now)
            b.files.append(f)
    session.commit()
    return (n_new, n_total)
