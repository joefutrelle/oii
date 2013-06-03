#!/bin/bash
export PYTHONPATH=/home/habcam/ic
cd /home/habcam/ic
LEARN=$(head -1 learn_bin.conf)
LOGS_DIR=/habcam/nmfs/proc/logs
while read bin_lid; do
    if [[ "$bin_lid" > "20130603_1730" ]]; then
	LOG_DIR=$LOGS_DIR/${bin_lid}
	mkdir -p $LOG_DIR
	LOGFILE=$LOG_DIR/${bin_lid}.$(date +%s).log
	/usr/bin/python ./oii/scripts/nosplit_lightfield_batch.py $bin_lid $LEARN > $LOGFILE
	/bin/gzip $LOGFILE
    fi
done < <\
(/usr/bin/find /habcam -maxdepth 5 -type d -regextype posix-egrep -regex /habcam/nmfs/[0-9]{6}.*[0-9]{8}*_[0-9]{4}* \
-exec basename {} \;)
