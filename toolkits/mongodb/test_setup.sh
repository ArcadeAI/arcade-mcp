#!/bin/bash

# install mongosh to load sample data
sudo apt-get update
sudo apt-get install -y wget gnupg
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-mongosh

# Run mongodb container
docker run -d --name some-mongodb-server -p 27017:27017 mongo
