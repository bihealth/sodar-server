#!/usr/bin/env bash

echo "***********************************************"
echo "Installing PostgreSQL v11"
echo "***********************************************"
add-apt-repository -y "deb http://apt.postgresql.org/pub/repos/apt/ focal-pgdg main"
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
apt-get -y update
apt-get -y install postgresql-11
