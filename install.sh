#!/bin/bash

sudo -i
apt update
apt install -y python3-venv python3-pip python3-dev build-essential \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libmtdev-dev libgl1-mesa-dev libgles2-mesa-dev \
  libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  zlib1g-dev libjpeg-dev
mkdir /opt/paketmanager
cp * /opt/paketmanager
cd /opt/paketmanager
python3 -m venv venv
source venv/bin/activate
python3 -m install --upgrade-pip
pip install -r requirements.txt
echo "installed successfully to /opt/paketmanager"
