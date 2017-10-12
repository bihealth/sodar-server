#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Chrome + Driver for UI Testing"
echo "***********************************************"

# Version
CHROME_DRIVER_VERSION=2.33

# Install dependencies
apt-get -y install default-jre unzip
apt-get -y install libxpm4 libxrender1 libgtk2.0-0 libnss3 libgconf-2-4
apt-get -y install xvfb gtk2-engines-pixbuf

# Install Chrome Driver
wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/
unzip ~/chromedriver_linux64.zip -d ~/
mv -f ~/chromedriver /usr/bin/chromedriver
chmod ugo+rx /usr/bin/chromedriver

# Install Google Chrome
wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -P ~/
sudo dpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb
