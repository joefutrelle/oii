#!/bin/bash
psql -h squalus.whoi.edu habcam_2013 -t -A -F, -c \
    "select distinct(imagename2bin(imagename)) from imagelist where assignment_id in ('201309', '201310')" \
    --output='assignment_bins.csv'

while read BIN_LID; do
    DIR=/habcamserver/assignments/proc/$(echo $BIN_LID | sed -e 's#\(\([0-9]\{6\}\)[0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)#\2/\1/\1_\3/\1_\3\4/#')
    mkdir -p $DIR
    OUT=$DIR/${BIN_LID}_alt.csv
    echo "Writing $BIN_LID assignment alts to $OUT ..."
    psql -h squalus.whoi.edu habcam_2013 -t -A -F, -c \
	    "select imageid || '.tif', x, y, parallax_alt from burton_alts where imagename2bin(imageid) = '"${BIN_LID}"';" \
	    --output=$OUT
done < assignment_bins.csv

