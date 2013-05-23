echo 'Checking out code ...'
svn co --non-interactive --trust-server-cert https://beagle.whoi.edu/svn/ibt/trunk/oii /home/$SYSTEM_USER/oii

echo 'Configuring local data resolver ...'
RAW_ROOTS=''
for DATA_DIR in $DATA_DIRS; do
    RAW_ROOTS="$RAW_ROOTS <hit name=\"root\">$DATA_DIR</hit>"
done
cat /home/$SYSTEM_USER/oii/ifcb/resolver_template.txt | \
 sed -e "s/@TIME_SERIES@/$TIME_SERIES/g" \
     -e "s#@RAW_ROOTS@#$RAW_ROOTS#g" \
> /home/$SYSTEM_USER/resolver.xml

echo "Creating configuration files..."
cat > /etc/supervisor/conf.d/supervisor_accession.conf <<EOF
[program:${TIME_SERIES}_accession]
user=$SYSTEM_USER
umask=002
directory=/home/$SYSTEM_USER
environment=PYTHONPATH="/home/$SYSTEM_USER"
command=celery --config=celery_config worker -A oii.ifcb.workflow.accession -c 1 --queue=mvco_test_accession --purge
autorestart=true
EOF

cat > /home/$SYSTEM_USER/accession.conf <<EOF
resolver = /home/$SYSTEM_USER/resolver.xml
[$TIME_SERIES]
psql_connect = user=$DATABASE_USER password=$DATABASE_PASSWORD dbname=$TIME_SERIES
year_pattern = ....
EOF

cat > /home/$SYSTEM_USER/dashboard.conf <<EOF
resolver = /home/$SYSTEM_USER/resolver.xml
psql_connect = user=$DATABASE_USER password=$DATABASE_PASSWORD
EOF

cat > /home/$SYSTEM_USER/dashboard.wsgi <<EOF
import os
import sys

sys.path.insert(0,'/home/$SYSTEM_USER')

os.environ['IFCB_CONFIG_FILE'] = '/home/$SYSTEM_USER/dashboard.conf'

from oii.ifcb.webapi import app as application
EOF

cat > /home/$SYSTEM_USER/apache_conf <<EOF
  WSGIDaemonProcess ifcb_dashboard threads=6
  WSGIScriptAlias / /home/$SYSTEM_USER/dashboard.wsgi

  <Directory "/home/$SYSTEM_USER/">
     WSGIProcessGroup ifcb_dashboard
     WSGIApplicationGroup %{GLOBAL}
     Order deny,allow
     Allow from all
 </Directory>
EOF

cat > /home/$SYSTEM_USER/accession.sh <<EOF
#!/bin/sh
cd /home/$SYSTEM_USER
export PYTHONPATH=.
TIME_SERIES=\$1
/usr/local/bin/celery --config=celery_config call oii.ifcb.workflow.accession.accede --args="[\"/home/$SYSTEM_USER/accession.conf\", \"\${TIME_SERIES}\"]" --queue=\${TIME_SERIES}_accession
EOF

cp celery_config.py /home/$SYSTEM_USER

chown -R $SYSTEM_USER:$SYSTEM_USER /home/$SYSTEM_USER

echo 'Starting accession workers ...'
supervisorctl update

echo 'Adding scheduled task ...'
tmp=/tmp/cronmod$$
echo "*/8 * * * * /bin/bash /home/$SYSTEM_USER/accession.sh $TIME_SERIES > /dev/null" > $tmp
sudo -u $SYSTEM_USER crontab $tmp
