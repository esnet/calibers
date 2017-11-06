#!/bin/bash

#hacky script to configure the default proxmox debian image to calibers
#nate hates csh
chsh -s /bin/bash rootnh
chsh -s /bin/bash nhanford

#nasty call to the apt cli to remove old iperf3 images that ship stock
apt -y purge iperf3 libiperf0

#Add repos

wget -O /etc/apt/sources.list.d/perfsonar-jessie-4.0.list http://downloads.perfsonar.net/debian/perfsonar-jessie-4.0.list
wget -qO - http://downloads.perfsonar.net/debian/perfsonar-debian-official.gpg.key | apt-key add -
wget https://downloads.globus.org/toolkit/gt6/stable/installers/repo/deb/globus-toolkit-repo_latest_all.deb

#More unsafe calls to the apt cli
dpkg -i ./globus-toolkit-repo_latest_all.deb
apt -yf install
dpkg -i ./globus-toolkit-repo_latest_all.deb
apt update
apt -y install git perfsonar-tools globus-gridftp python-pip
pip install flask

