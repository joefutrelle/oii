echo "Preparing to install dependencies ..."

apt-get update

# just to help
apt-get install -y emacs23-nox subversion curl

echo "Installing dependencies ..."

apt-get install -y build-essential postgresql rabbitmq-server
apt-get install -y python-dev python-lxml python-psycopg2 supervisor

sudo apt-get install -y python-pip 

for m in pytz celery; do
    pip install $m
done

