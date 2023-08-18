#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Chrome + Chromedriver for UI Testing"
echo "***********************************************"

# Install dependencies
sudo apt-get update
sudo apt-get install -y unzip xvfb libxi6 libgconf-2-4

# Install Chrome
wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -P ~/
sudo dpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb
sudo apt-get -f install -y
rm ~/google-chrome-stable_current_amd64.deb

# Install Chromedriver
sh $(dirname "$0")/install_chromedriver.sh
