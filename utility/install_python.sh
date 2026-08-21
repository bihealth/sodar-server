#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Python 3.13"
echo "***********************************************"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get -y update
apt-get -y install python3.13 python3.13-dev python3.13-venv python3.13-gdbm
curl https://bootstrap.pypa.io/get-pip.py | sudo -H python3.13
