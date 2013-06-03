#!/bin/bash
if [ $(ps aux | grep doitall | grep -v grep | wc -l) -eq 0 ]; then
    /bin/bash /home/habcam/ic/doitall.sh
fi