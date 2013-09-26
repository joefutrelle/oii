#!/bin/sh
# must run as root

# must be current on aptitude

apt-get update

# upgrade gcc so we can build numpy

#apt-get upgrade -y gcc
# FIXME this is the wrong way to do that.

# install required aptitude packages

apt-get install -y libxml2-dev libxslt-dev zlib1g-dev cython python-pip python-lxml python-imaging python-pika python-flask liblapack-dev gfortran libblas-dev g++ python-dev python-pip libfreeimage3 python-numpy python-scipy

# now use pip for remaining python packages

pip install pytz
pip install scikits-image
pip install scikits.learn
pip install phasepack
