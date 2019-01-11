#!/usr/bin/env bash

echo "***********************************************"
echo "Installing PostgreSQL 9.6"
echo "***********************************************"
add-apt-repository -y "deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main"
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
apt-get -y update
apt-get -y install postgresql-9.6
