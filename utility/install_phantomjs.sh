#!/bin/bash

# Source: https://dezoito.github.io/2016/05/11/django-gitlab-continuous-integration-phantomjs.html

echo "***********************************************"
echo "Installing PhantomJS"
echo "***********************************************"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

PHANTOM_VERSION="phantomjs-1.9.8"
ARCH=$(uname -m)

if ! [ $ARCH = "x86_64" ]; then
    $ARCH="i686"
fi

PHANTOM_JS="$PHANTOM_VERSION-linux-$ARCH"

# apt-get update
apt-get install build-essential chrpath libssl-dev libxft-dev -y
apt-get install libfreetype6 libfreetype6-dev -y
apt-get install libfontconfig1 libfontconfig1-dev -y

cd ~
wget https://bitbucket.org/ariya/phantomjs/downloads/$PHANTOM_JS.tar.bz2
tar xvjf $PHANTOM_JS.tar.bz2

mv $PHANTOM_JS /usr/local/share
ln -sf /usr/local/share/$PHANTOM_JS/bin/phantomjs /usr/local/bin