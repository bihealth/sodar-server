#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Python 3.11"
echo "***********************************************"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get -y update
apt-get -y install python3.11 python3.11-dev python3.11-venv python3.11-gdbm
curl https://bootstrap.pypa.io/get-pip.py | sudo -H python3.11
