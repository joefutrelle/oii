echo 'Downloading IFCB data ...'

# these are just for testing
DAY=IFCB5_2013_141
BIN=${DAY}_113957
DATA_DIR=/home/$SYSTEM_USER/data/IFCB5_2013_141

mkdir -p $DATA_DIR
for f in hdr adc roi; do
    curl http://ifcb-data.whoi.edu/mvco/${BIN}.${f} > $DATA_DIR/${BIN}.${f}
done

chown -R $SYSTEM_USER:$SYSTEM_USER /home/$SYSTEM_USER/data

echo 'Initiating accession ...'
sudo -u $SYSTEM_USER bash /home/$SYSTEM_USER/accession.sh $TIME_SERIES

echo 'Waiting one minute ...'
sleep 60

echo 'Tailing logs ...'
tail /var/log/supervisor/*.log

echo 'Querying database ...'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from bins'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from fixity'
