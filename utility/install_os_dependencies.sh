#!/usr/bin/env bash

echo "***********************************************"
echo "Apt-get update"
echo "***********************************************"
apt-get -y update

echo "***********************************************"
echo "Installing general OS dependencies"
echo "***********************************************"
apt-get -y install build-essential

echo "***********************************************"
echo "Installing Pillow and pylibmc dependencies"
echo "***********************************************"
apt-get -y install zlib1g-dev
apt-get -y install libtiff5-dev
apt-get -y install libjpeg8-dev
apt-get -y install libfreetype6-dev
apt-get -y install liblcms2-dev
apt-get -y install libwebp-dev

echo "***********************************************"
echo "Installing Postgresql and psycopg2 dependencies"
echo "***********************************************"
apt-get -y install libpq-dev

echo "***********************************************"
echo "Installing django-extensions dependencies"
echo "***********************************************"
apt-get -y install graphviz-dev
