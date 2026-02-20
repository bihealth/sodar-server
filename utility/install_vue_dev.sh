#!/usr/bin/env bash
echo "***********************************************"
echo "Installing Node.js"
echo "***********************************************"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt-get update
sudo apt-get install nodejs -y

# TODO: Remove once Vue 2 app has been retired
echo "***********************************************"
echo "Installing Vue CLI and Init"
echo "***********************************************"
npm install -g @vue/cli
npm install -g @vue/cli-init

# TODO: Vue3 app dev dependencies here if needed
