from oii.procutil import Process
import sys
from oii.utils import Struct
import os
import re

if __name__=='__main__':
    exec_path = '/usr/local/bin/ImageStack'
    script = ' '.join([exec_path,
            '-load %(img_in)s',
            '-demosaic 1 0 1',
            '-crop 0 0 1360 1024',
            '-dup -normalize -scale 2.5 -clamp -save %(img_out)s_before.png -pop',
            '-dup',
            '-rectfilter %(filter_size)s',
            '-pull 1 -subtract',
            '-normalize -scale 2.5 -clamp',
            '-save %(img_out)s'
            ])
    ims = Process(script)
    in_dir='/Users/jfutrelle/Pictures/habcamv4/leg1_stereo'
    out_dir='/Users/jfutrelle/Pictures/habcamv4/leg1_stereo_out_v3'
    for f in os.listdir(in_dir):
        if re.match('.*\.tif$',f):
            img_in = os.path.join(in_dir,f)
            img_out = os.path.join(out_dir,f)
            for msg in ims.run(dict(img_in=img_in,filter_size=501,img_out=img_out)):
                print msg['message']
    

    
