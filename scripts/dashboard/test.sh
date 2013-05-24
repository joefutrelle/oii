echo 'Downloading IFCB data ...'

SYSTEM_USER=ifcb

# MVCO data
TIME_SERIES=mvco_test

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

echo 'Waiting 15s ...'
sleep 15

echo 'Tailing logs ...'
tail /var/log/supervisor/*.log

echo 'Querying database ...'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from bins'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from fixity'

# Saltpond data
TIME_SERIES=saltpond_test

# these are just for testing
YEAR=D2013
DAY=D20130522
BIN=D20130522T140308_IFCB012
DATA_DIR=/home/$SYSTEM_USER/data2/$YEAR/$DAY

mkdir -p $DATA_DIR
for f in hdr adc roi; do
    curl http://ifcb-data.whoi.edu/mvco/${BIN}.${f} > $DATA_DIR/${BIN}.${f}
done

chown -R $SYSTEM_USER:$SYSTEM_USER /home/$SYSTEM_USER/data2

echo 'Initiating accession ...'
sudo -u $SYSTEM_USER bash /home/$SYSTEM_USER/accession.sh $TIME_SERIES

echo 'Waiting 15s ...'
sleep 15

echo 'Tailing logs ...'
tail /var/log/supervisor/*.log

echo 'Querying database ...'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from bins'
sudo -u postgres psql $TIME_SERIES -P pager=off -c 'select * from fixity'
