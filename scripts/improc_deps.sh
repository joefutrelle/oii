#!/bin/sh
# must run as root

# must be current on aptitude

sudo apt-get update

# upgrade gcc so we can build numpy

#apt-get upgrade -y gcc
# FIXME this is the wrong way to do that.

# install required aptitude packages

sudo apt-get install -y libxml2-dev libxslt-dev zlib1g-dev cython python-pip python-lxml python-imaging python-pika python-flask liblapack-dev gfortran libblas-dev g++ python-dev python-pip libfreeimage3 python-numpy python-scipy python-matplotlib fftw3-dev

# now use pip for remaining python packages

sudo -H pip install pytz
sudo -H pip install scikits-image
sudo -H pip install scikits.learn
sudo -H pip install pyfftw
sudo -H pip install anfft
sudo -H pip install phasepack==1.1

