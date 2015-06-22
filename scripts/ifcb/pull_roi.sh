#!/bin/bash
# this script reads ROI images from IFCB data and converts them to pngs
# it depends on ImageMagick
# usage: bash pull_roi.sh {adc file} {roi file} {roi number}
ADC=$1 # IFCB ADC file
ROI=$2 # IFCB ROI file

# determine the number of ROIs in the file
N=$(wc -l $ADC | sed -e 's/ .*//')
I=$N

while [ $I -gt 0 ]; do
    OF=rois/$(basename $ADC)_${I}.png
    # get width, height, and byte offset from the ADC file
    read width height offset <<<$(awk -F, '{print $12,$13,$14}' $ADC | head -${I}  | tail -1)
    echo ROI $I is at $width $height $offset
    # pull the bytes with dd, then use ImageMagick to convert them to a png
    dd skip=$(($offset - 1)) count=$(($width * $height)) if=$ROI bs=1 | convert -size ${width}x${height} -depth 8 gray:- $OF
    I=$((I - 1))
done


