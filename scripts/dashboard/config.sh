echo 'Checking out code ...'
svn co --non-interactive --trust-server-cert https://beagle.whoi.edu/svn/ibt/trunk/oii /home/$SYSTEM_USER/oii

echo 'Writing configuration templates ...'

cp /home/$SYSTEM_USER/oii/ifcb/resolver_template.txt /home/$SYSTEM_USER/resolver.xml
sed -i /home/$SYSTEM_USER/resolver.xml -e "s#{{base_url}}#$BASE_URL#"

cat > /home/$SYSTEM_USER/accession.conf <<EOF
resolver = /home/$SYSTEM_USER/resolver.xml
EOF

cat > /home/$SYSTEM_USER/accession.sh <<EOF
#!/bin/sh
cd /home/$SYSTEM_USER
export PYTHONPATH=.
TIME_SERIES=\$1
/usr/local/bin/celery --config=celery_config call oii.ifcb.workflow.accession.accede --args="[\"/home/$SYSTEM_USER/accession.conf\", \"\${TIME_SERIES}\"]" --queue=\${TIME_SERIES}_accession
EOF

echo 'Configuring web application ...'

cat > /home/$SYSTEM_USER/dashboard.conf <<EOF
resolver = /home/$SYSTEM_USER/resolver.xml
psql_connect = host=localhost user=$DATABASE_USER password=$DATABASE_PASSWORD
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

cp celery_config.py /home/$SYSTEM_USER

chown -R $SYSTEM_USER:$SYSTEM_USER /home/$SYSTEM_USER
