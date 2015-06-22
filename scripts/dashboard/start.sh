echo 'Starting accession workers ...'
supervisorctl update

echo 'Adding scheduled accession task ...'

tmp=/tmp/cronmod$$
echo "*/8 * * * * /bin/bash /home/$SYSTEM_USER/accession.sh $TIME_SERIES > /dev/null" > $tmp
sudo -u $SYSTEM_USER crontab $tmp
