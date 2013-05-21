
echo "Adding user $SYSTEM_USER ..."
adduser --disabled-password --gecos "" $SYSTEM_USER

echo "Adding PostgreSQL user $DATABASE_USER ..."
sudo -u postgres createuser $DATABASE_USER -DRS
sudo -u postgres createdb $TIME_SERIES
sudo -u postgres psql -c "alter user $DATABASE_USER with encrypted password '$DATABASE_PASSWORD'"
sudo -u postgres psql -c "grant all privileges on database $TIME_SERIES to $DATABASE_USER"

echo "Creating database tables and indexes ..."
sudo -u postgres psql $TIME_SERIES -f ifcb_schema.sql

