import sys
from oii.config import get_config
from oii.habcam.image.imagestack import ImageStackWorker, cli

class HabcamRedCyan(ImageStackWorker):
    def get_script(self):
        DEBAYER='-demosaic 1 0 1'
        # crop: chop image in half down the middle
        CROP_L='-crop 0 0 1360 1024'
        CROP_R='-crop 1360 0 1360 1024'
        # illum_correct: subtract LPF of image from image (using large rectangular filter)
        filter_size=501
        ILLUM_CORRECT="-dup -rectfilter 501 -pull 1 -subtract"
        # adjust contrast by normalizing mean and stddev
        CONTRAST='-normalize -eval "0.4 + (((val-mean(c))/stddev(c)) * 0.15)"'
        ALIGN='-align perspective'
        GRAYSCALE='-colorconvert rgb y -colorconvert y rgb'
        CYAN_ONLY='-evalchannels 0 val val'
        RED_ONLY='-colorconvert rgb y -evalchannels val 0 0'
        TRIM='-evalchannels "[1]+[2] > 0 ? val : 0" "val" "val" -crop'
        return ' '.join([self.config.imagestack_exec_path,
                         '-load %(img_in)s',
                         DEBAYER,
                         '-dup',
                         CROP_L, ILLUM_CORRECT, CONTRAST,
                         '-pull 1',
                         CROP_R, ILLUM_CORRECT, CONTRAST,
                         ALIGN, GRAYSCALE, CYAN_ONLY, '-pull 1', GRAYSCALE, RED_ONLY, '-add',
                         TRIM,
                         '-save %(img_out)s'
                         ])

# usage:
# python stereo.py {config file} {command} {arguments}
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
    hl = HabcamRedCyan(get_config(sys.argv[1]))
    cli(hl, sys.argv)

