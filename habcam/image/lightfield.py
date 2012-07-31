import sys
from oii.config import get_config
from oii.habcam.image.imagestack import ImageStackWorker, cli

class HabcamLightfieldNhv(ImageStackWorker):
    """Note that this impl uses NHV's modded version of ImageStack containing wls2 and histoadapt operators"""
    def get_script(self):
        return ' '.join([self.config.imagestack_exec_path,
                         '-load %(img_in)s',
                         '-crop 0 0 1360 1024',
                         '-demosaic 1 0 1',
                         '-colorconvert rgb lab',
                         '-dup',
                         '-downsample',
                         '-wls2 2.5 0.25 100 0.025',
                         '-upsample',
                         '-add',
                         '-histoadapt 0.45 1.25 2 10 4',
                         '-colorconvert lab rgb',
                         '-clamp',
                         '-save %(img_out)s'
                         ])

class HabcamLightfieldJoe(ImageStackWorker):
    def get_script(self):
        return ' '.join([self.config.imagestack_exec_path,
                         '-load %(img_in)s',
                         '-demosaic 1 0 1',
                         '-crop 0 0 1360 1024',
                         '-dup',
                         '-rectfilter %(filter_size)s',
                         '-pull 1 -subtract',
                         '-normalize -scale 2.5 -clamp',
                         '-save %(img_out)s'
                         ])
    def get_parameters(self):
        p = super(HabcamLighfieldJoe,self).get_parameters()
        p['filter_size'] = 501
        return p

# usage:
# python lightfield.py {config file} {command} {arguments}
# commands:
# q (file1, file2, file3, ... filen)
#   enqueue files for processing
# q -
#   read a list of files to process from stdin
# r
#   requeue failed processing jobs
# w
#   run as a worker
# log
#   show logging messages as they come in
if __name__=='__main__':
    hl = HabcamLightfieldNhv(get_config(sys.argv[1]))
    cli(hl, sys.argv)

