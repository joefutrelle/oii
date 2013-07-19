import sys
import os
import re
import urllib2 as urllib
import json
import logging
import time

import numpy as np
from skimage import img_as_float
from skimage.io import imread, imsave
from skimage.transform import resize

from oii.habcam.lightfield.altitude import stereo2altitude

from oii.resolver import parse_stream
from oii.iopipes import StagedInputFile, UrlSource, LocalFileSource, drain, LocalFileSink
from oii.csvio import read_csv
from oii.procutil import Process
from oii.image.demosaic import demosaic
from oii.utils import remove_extension, change_extension

from lightfield_config import *

lgfmt = '%(asctime)-15s %(message)s'
logging.basicConfig(format=lgfmt,stream=sys.stdout,level=logging.DEBUG)

resolver = parse_stream(RESOLVER)

def mkdirs(d):
    """Create directories"""
    if not os.path.exists(d):
        os.makedirs(d)
        logging.info('created directory %s' % d)
    else:
        logging.info('directory %s exists' % d)
    return d

def scratch(bin_lid,suffix=''):
    """Compute path to scratch space"""
    return resolver['scratch'].resolve(pid=bin_lid,suffix=suffix).value
    #return os.path.join(SCRATCH,bin_lid,suffix)

def list_images(bin_lid):
    """List all images in a bin by LID"""
    imgdata = resolver['img'].resolve(pid=bin_lid).value
    rows = list(read_csv(LocalFileSource(imgdata)))
    return [r[0] for r in rows[::IMAGELIST_STEP]][:NUM_CORRECT]

def read_image(imagename):
    pathname = resolver['cfa_LR'].resolve(pid=imagename).value
    then = time.time()
    img = imread(pathname,plugin='freeimage')
    logging.info('completed reading %s in %.3f s' % (pathname, time.time() - then))
    return img

def metadata2eic(bin_lid,parallax):
    """Convert bin image metadata to CSV"""
    #imagename,lat,lon,head,pitch,roll,alt1,alt2,depth,s,t,o2,cdom,chlorophyll,backscatter,therm
    (PITCH_COL, ROLL_COL) = (4, 5)
    fields = ['imagename', 'alt', 'pitch','roll']
    imgdata = resolver['img'].resolve(pid=bin_lid).value
    logging.info('reading CSV data from .img file %s' % imgdata)
    (pitch,roll) = ({}, {})
    for row in read_csv(LocalFileSource(imgdata)):
        imagename = remove_extension(row[0])
        try:
            pitch[imagename] = row[PITCH_COL]
            roll[imagename] = row[ROLL_COL]
        except KeyError:
            pass
    logging.info('merging with parallax-based altitude from %s' % parallax)
    for l in open(parallax):
        (imagename, _, _, alt) = re.split(r',',l.rstrip())
        try:
            yield [imagename, alt, pitch[imagename], roll[imagename]]
        except KeyError:
            pass

def fetch_eic(bin_lid,suffix='',tmp=None,skip=[]):
    """Fetch bin image metadata and write CSV to file"""
    if tmp is None:
        tmp = mkdirs(os.path.join(scratch(bin_lid),'tmp'))
    parallax = os.path.join(scratch(bin_lid),bin_lid+'_alt.csv')
    eic = os.path.join(tmp,'%s%s.eic' % (bin_lid, suffix))
    with open(eic,'w') as fout:
        for tup in metadata2eic(bin_lid,parallax):
            imagename = remove_extension(tup[0])
            if imagename not in skip:
                tup[0] = imagename + '.tif'
                print >> fout, ' '.join(tup)
    return eic

def as_tiff(imagename):
    """Change extension on imagename to 'tif'"""
    return change_extension(imagename,'tif')

def alt(bin_lid):
    tmp = mkdirs(scratch(bin_lid))
    csv_filename = os.path.join(tmp,bin_lid+'_alt.csv')
    logging.info('listing images for %s' % bin_lid)
    imagenames = [remove_extension(i) for i in list_images(bin_lid)]
    logging.info('looking for existing altitude data...')
    already_done = []
    if os.path.exists(csv_filename):
        for row in read_csv(LocalFileSource(csv_filename)):
            already_done += [row[0]]
    logging.info('found %d existing altitude records' % len(already_done))
    if len(already_done) == -1:
        logging.info('emptying CSV file ...')
        with open(csv_filename,'w') as csv_out:
            pass
    pids = []
    for n in range(NUM_PROCS):
        pid = os.fork()
        if pid == 0:
            for imagename in imagenames[n::NUM_PROCS]: # FIXME remove n+20
                if imagename not in already_done:
                    tif = img_as_float(read_image(imagename+'.tif'))
                    logging.info('[%d] START aligning %s' % (n, imagename))
                    x,y,m = stereo2altitude(tif)
                    line = '%s,%d,%d,%.2f' % (imagename,x,y,m) 
                    logging.info('[%d] DONE aligned %s' % (n, line))
                    with open(csv_filename,'a') as csv_out:
                        print >>csv_out, line
                        csv_out.flush()
            os._exit(0)
        else:
            logging.info('spawned process %d' % pid)
            pids += [pid]
    for pid in pids:
        logging.info('waiting for process %d' % pid)
        os.waitpid(pid,0)
        logging.info('joined alignment process %d' % pid)
    # now sort file
    logging.info('sorting CSV data...')
    rows = list(read_csv(LocalFileSource(csv_filename)))
    rows = sorted(rows, key=lambda r: r[0])
    csv_out = csv_filename # same as in
    with open(csv_out,'w') as co:
        for row in rows:
            print >>co, ','.join([row[n] for n in range(4)])
    logging.info('wrote CSV data to %s' % csv_out)

def stage(bin_lid):
    imagenames = list(list_images(bin_lid))
    (h,w) = (0,0)
    LR_dir = None
    for imagename in imagenames:
        if h == 0:
            (h,w) = read_image(imagename).shape
            pathname = resolver['cfa_LR'].resolve(pid=imagename).value
            LR_dir = os.path.dirname(pathname)
            return (h,w),LR_dir

def learn(bin_lid):
    (h,w),LR_dir = stage(bin_lid)
    pids = []
    for LR in 'LR':
        pid = os.fork()
        if pid == 0: # subprocess
            # provision temp space
            tmp = mkdirs(scratch(bin_lid,'tmp_' + LR))
            # fetch eic
            eic = fetch_eic(bin_lid)
            # construct param file
            lightmap_dir = mkdirs(scratch(bin_lid,bin_lid + '_lightmap_' + LR))
            lightmap = os.path.join(lightmap_dir,bin_lid+'_lightmap_' + LR)
            if os.path.exists(lightmap):
                logging.info('lightmap exists: %s' % lightmap)
            else: # lightmap doesn't exist
                learn_tmp =  mkdirs(scratch(bin_lid,bin_lid + '_lightmap_tmp_' + LR))
                param = os.path.join(tmp,bin_lid + '_learn.txt')
                # produce param file
                logging.info('writing param file %s' % param)
                with open(param,'w') as fout:
                    print >> fout, 'imagedir %s' % LR_dir
                    print >> fout, 'metafile %s' % re.sub(r'/([^/]+)$',r'/ \1',eic)
                    print >> fout, 'tmpdir %s' % learn_tmp
                    print >> fout, 'save %s' % lightmap 
                    for k,v in DEFAULT_IC_CONFIG.items():
                        print >> fout, '%s %s' % (k,str(v))
                    print >> fout, 'binary_format'
                    print >> fout, 'num_to_process %d' % NUM_LEARN
                    print >> fout, 'num_rows %d' % h
                    print >> fout, 'num_cols %d' % (w/2)
                    print >> fout, 'top %d' % 0
                    if LR == 'L':
                        print >> fout, 'left %d' % 0
                    else:
                        print >> fout, 'left %d' % (w/2)
                    print >> fout, PATTERN
                    print >> fout, 'scallop_eic'
                    print >> fout, 'learn'
                # now learn
                learn = Process('"%s" "%s"' % (IC_EXEC, param))
                for line in learn.run():
                    logging.info(line['message'])
            os._exit(0)
        else:
            pids += [pid]
    # done
    for pid in pids:
        os.waitpid(pid,0)
        logging.info('joined learn process %s' % pid)

def correct(bin_lid,learn_lid=None):
    (h,w),LR_dir = stage(bin_lid)
    if learn_lid is None:
        learn_lid = bin_lid
    # provision temp space
    tmp = mkdirs(scratch(bin_lid,'tmp'))
    for LR in 'LR':
        # check for lightmap existence
        lightmap_dir = mkdirs(scratch(learn_lid,learn_lid + '_lightmap_' + LR))
        lightmap = os.path.join(lightmap_dir,learn_lid+'_lightmap_' + LR)
        if not os.path.exists(lightmap):
            logging.info('requested lightmap does not exist, skipping correct phase')
            return
        # check for existing output
        logging.info('checking for existing corrected images...')
        outdir = mkdirs(scratch(bin_lid,bin_lid + '_cfa_illum_' + LR))
        skip = []
        for fn in os.listdir(outdir):
            imagename = re.sub('_cfa_illum_' + LR + '.tif','',fn)
            skip += [remove_extension(imagename)]
        logging.info('found %d existing corrected images ...' % len(skip))
        outdir = mkdirs(scratch(bin_lid,bin_lid + '_cfa_illum_' + LR))
        # fetch eic
        eic = fetch_eic(bin_lid,suffix='_'+LR,skip=skip)
        # now see if that file is empty
        if os.stat(eic)[6] == 0:
            logging.info('no images to correct, skipping %s/%s' % (bin_lid, LR))
            continue
        # construct param file
        correct_tmp = mkdirs(scratch(bin_lid,bin_lid + '_correct_tmp_' + LR))
        param = os.path.join(tmp,bin_lid + '_correct.txt')
        # produce param file
        logging.info('writing param file %s' % param)
        with open(param,'w') as fout:
            print >> fout, 'imagedir %s' % LR_dir
            print >> fout, 'outdir %s' % outdir
            print >> fout, 'metafile %s' % re.sub(r'/([^/]+)$',r'/ \1',eic)
            print >> fout, 'tmpdir %s' % correct_tmp
            print >> fout, 'load %s' % lightmap 
            print >> fout, 'num_to_process %d' % NUM_CORRECT
            for k,v in DEFAULT_IC_CONFIG.items():
                print >> fout, '%s %s' % (k,str(v))
            print >> fout, 'binary_format'
            print >> fout, 'num_rows %d' % h
            print >> fout, 'num_cols %d' % (w/2)
            print >> fout, 'top %d' % 0
            if LR == 'L':
                print >> fout, 'left %d' % 0
            else:
                print >> fout, 'left %d' % (w/2)
            print >> fout, PATTERN
            print >> fout, 'scallop_eic'
            print >> fout, 'correct'
        # now correct
        logging.info('correcting %s' % bin_lid)
        correct = Process('"%s" "%s"' % (IC_EXEC, param))
        for line in correct.run():
            logging.info(line['message'])

def internal_merge_one(cfa_L_path, cfa_R_path, cfa_LR_path):
    cfa_L = imread(cfa_L_path, plugin='freeimage')
    cfa_R = imread(cfa_R_path, plugin='freeimage')
    cfa_LR = np.concatenate((cfa_L, cfa_R), axis=1)
    imsave(cfa_LR_path,cfa_LR, plugin='freeimage')
    logging.info('merged %s' % cfa_LR_path)

def merge_one(cfa_L, cfa_R, cfa_LR):
    merge = Process('"%s" -l "%s" -r "%s" -o "%s" -v' % (MERGE_EXEC, cfa_L, cfa_R, cfa_LR))
    for line in merge.run():
        logging.info(line['message'])

def merge(bin_lid):
    LR_dir = mkdirs(scratch(bin_lid,bin_lid + '_cfa_illum_LR'))
    # now demosaic
    L_dir = scratch(bin_lid,bin_lid + '_cfa_illum_L')
    R_dir = scratch(bin_lid,bin_lid + '_cfa_illum_R')
    if not os.path.exists(L_dir):
        logging.info('no left image directory to merge, skipping')
        return
    if not os.path.exists(R_dir):
        logging.info('no right image directory to merge, skipping')
        return
    imgs = sorted(os.listdir(L_dir))
    pids = []
    for n in range(NUM_PROCS):
        pid = os.fork()
        if pid == 0:
            for f in imgs[n::NUM_PROCS]:
                cfa_LR_path = os.path.join(LR_dir,re.sub(r'_?[a-zA-Z_.]+$','_cfa_illum_LR.tif',f))
                if os.path.exists(cfa_LR_path):
                    logging.info('merged image exists, skipping %s' % f)
                cfa_L_path = os.path.join(L_dir,f)
                cfa_R_path = os.path.join(R_dir,f)
                merge_one(cfa_L_path, cfa_R_path, cfa_LR_path);
                if os.path.exists(cfa_LR_path):
                    # if the output file exists, assume that it worked and delete L/R files
                    os.remove(cfa_L_path)
                    logging.info('DELETED %s' % cfa_L_path)
                    os.remove(cfa_R_path)
                    logging.info('DELETED %s' % cfa_R_path)
            os._exit(0)
        else:
            pids += [pid]
    for pid in pids:
        os.waitpid(pid,0)
        logging.info('joined merging process %d' % pid)

def rectify_list(inlist):
    rect = Process('"%s" -v -s -l "%s" -c "%s"' % (RECT_EXEC, inlist, CALIBRATION_DIR))
    for line in rect.run():
        logging.info(line['message'])

def rectify(bin_lid):
    illum_dir = mkdirs(scratch(bin_lid,bin_lid + '_cfa_illum_LR'))
    rect_dir = mkdirs(scratch(bin_lid,bin_lid + '_rgb_illum_LR'))
    tmp = mkdirs(os.path.join(scratch(bin_lid),'tmp'))
    imgs = sorted(os.listdir(illum_dir))
    pids = []
    for n in range(NUM_PROCS):
        pid = os.fork()
        if pid == 0:
            listfile = os.path.join(tmp, 'rect_list_%d' % n)
            count = 0
            with open(listfile,'w') as fout:
                for f in imgs[n::NUM_PROCS]:
                    intif = os.path.join(illum_dir,f)
                    outtif = os.path.join(rect_dir,re.sub(r'_?[a-zA-Z_.]+$','_rgb_illum_LR.tif',f))
                    if not os.path.exists(outtif):
                        print >> fout, '%s %s' % (intif, outtif)
                        count += 1
            if count > 0:
                rectify_list(listfile)
            os._exit(0)
        else:
            pids += [pid]
    for pid in pids:
        os.waitpid(pid,0)
        logging.info('joined rectification process %d' % pid)

if __name__=='__main__':
    bin_lid = sys.argv[1]
    learn_lid = None
    try:
        learn_lid = sys.argv[2]
        logging.info('using lightmap %s' % learn_lid)
        alt(learn_lid)
        learn(learn_lid)
    except IndexError:
        pass
    alt(bin_lid)
    if learn_lid is None:
        logging.info('no learn bin specified, using %s' % bin_lid)
        learn(bin_lid)
        learn_lid = bin_lid
    correct(bin_lid,learn_lid)
    merge(bin_lid)
    rectify(bin_lid)
