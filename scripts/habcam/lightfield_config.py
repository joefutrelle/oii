RESOLVER='/home/habcam/ic/oii/scripts/habcam_atsea.xml'
SCRATCH='/habcam/nmfs/proc'
PATTERN='rggb' # v4
IC_EXEC='/home/habcam/ic/IlluminationCorrection/multi-image-correction/illum_correct_average'
RECT_EXEC='/home/habcam/ic/stereoRectify/stereoRectify'
MERGE_EXEC='/home/habcam/ic/stereoRectify/merge_cfa_LR'

CALIBRATION_DIR='/home/habcam/ic/cal'

NUM_LEARN=300
NUM_CORRECT=5000
NUM_PROCS=12
NUM_THREADS=24

IMAGELIST_STEP=1
LEARN_STEP=1

DEFAULT_IC_CONFIG = {
    'delta': 0.1,
    'min_height': 1.0,
    'max_height': 4.0,
    'img_min': 0.3,
    'img_max': 3.1,
    'smooth': 32,
    'num_threads': NUM_THREADS
}
