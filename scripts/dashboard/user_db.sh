
echo "Adding user $SYSTEM_USER ..."
adduser --disabled-password --gecos "" $SYSTEM_USER

echo "Adding PostgreSQL user $DATABASE_USER ..."
sudo -u postgres createuser $DATABASE_USER -DRS
sudo -u postgres psql -c "alter user $DATABASE_USER with encrypted password '$DATABASE_PASSWORD'"

