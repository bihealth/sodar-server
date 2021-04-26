#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Python 3.8"
echo "***********************************************"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get -y update
apt-get -y install python3.8 python3.8-dev python3.8-venv
curl https://bootstrap.pypa.io/get-pip.py | sudo -H python3.8
