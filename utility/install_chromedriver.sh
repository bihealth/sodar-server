#!/usr/bin/env bash

echo "***********************************************"
echo "Installing Chromedriver for UI Testing         "
echo "***********************************************"

# NOTE: If depdendencies are missing, first run install_chrome.sh

# Install Chromedriver
CHROME_DRIVER_URL=$(python3 $(dirname "$0")/get_chromedriver_url.py)
wget -N $CHROME_DRIVER_URL -P ~/
unzip -o ~/chromedriver-linux64.zip -d ~/
rm ~/chromedriver-linux64.zip
sudo mv -f ~/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver
