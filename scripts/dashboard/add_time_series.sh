TIME_SERIES=$1
RAW_ROOTS=$2

echo "Adding time series $TIME_SERIES ..."

echo 'Configuring local data resolver ...'

tmp=$(mktemp)
cat > $tmp <<EOF
<value>$TIME_SERIES,$TIME_SERIES</value>
EOF
sed -i /home/$SYSTEM_USER/resolver.xml -e "/INSERT title/ r $tmp"

cat > $tmp <<EOF
    <match var="time_series" value="$TIME_SERIES">
      <var name="title">\${bot_name}</var>
      <var name="dbname">$TIME_SERIES</var>
      <hit/>
    </match>
EOF
sed -i /home/$SYSTEM_USER/resolver.xml -e "/INSERT dbname/ r $tmp"

cat > $tmp <<EOF
    <match var="time_series" value="$TIME_SERIES">
      <match var="product" value="raw">
EOF
for RAW_ROOT in $RAW_ROOTS; do
echo "Adding data directory $RAW_ROOT ..."
cat >> $tmp <<EOF
        <hit name="root">$RAW_ROOT</hit>
EOF
done
cat >> $tmp <<EOF
      </match>
      <match var="product" pattern="blob.*">@BLOB_ROOTS@</match>
      <match var="product" pattern="features">@FEATURE_ROOTS@</match>
    </match>
EOF
sed -i /home/$SYSTEM_USER/resolver.xml -e "/INSERT data_roots/ r $tmp"
rm $tmp

echo 'Configuring accession worker ...'

cat >> /etc/supervisor/conf.d/supervisor_accession.conf <<EOF
[program:${TIME_SERIES}_accession]
user=$SYSTEM_USER
umask=002
directory=/home/$SYSTEM_USER
environment=PYTHONPATH="/home/$SYSTEM_USER"
command=celery --config=celery_config worker -A oii.ifcb.workflow.accession -c 1 --queue=${TIME_SERIES}_accession --purge
autorestart=true
EOF

cat >> /home/$SYSTEM_USER/accession.conf <<EOF
[$TIME_SERIES]
psql_connect = user=$DATABASE_USER password=$DATABASE_PASSWORD dbname=$TIME_SERIES
year_pattern = ....
EOF

echo "Creating database for $TIME_SERIES ..."

sudo -u postgres createdb $TIME_SERIES
sudo -u postgres psql -c "grant all privileges on database $TIME_SERIES to $DATABASE_USER"

echo "Creating database tables and indexes ..."
sudo -u postgres psql $TIME_SERIES -f ifcb_schema.sql
