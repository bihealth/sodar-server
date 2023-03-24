#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Chromedriver for UI Testing         "
echo "***********************************************"

# Install dependencies
sudo apt-get update
sudo apt-get install -y unzip xvfb libxi6 libgconf-2-4

# Install ChromeDriver
CHROME_DRIVER_VERSION=$(curl http://chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/
unzip ~/chromedriver_linux64.zip -d ~/
rm ~/chromedriver_linux64.zip
sudo mv -f ~/chromedriver /usr/local/bin/chromedriver
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver
