#!/bin/bash

# execute before export my_passwd=xxxxxx

# add application environ values to .bashrc
cat ~/work/add_env_in_bashrc.txt >> ~/.bashrc

echo $my_passwd | sudo --stdin apt update && sudo apt -y upgrade
# headless os not installed.
echo $my_passwd | sudo --stdin apt -y install python3-venv sqlite3 pigpio i2c-tools tree

# Create Virtual Python environment.
mkdir py_venv
cd py_venv
python3 -m venv py37_pigpio
. py37_pigpio/bin/activate
pip install -U pip
pip install -r ~/work/py_venv/requirements_pigpio.txt
deactivate
cd ~/

# load PATH_WEATHER_DB
. ~/work/add_env_in_bashrc.txt
# Create weather database and tables by SQLite3
echo "Database file: $PATH_WEATHER_DB"
sqlite3 $PATH_WEATHER_DB < ~/db/weather_db.sql

# Enable pigpiod.service
echo $my_passwd | sudo --stdin systemctl enable pigpiod.service

# Enable application services
echo $my_passwd | { sudo --stdin cp ~/work/etc/default/switch-to-poweroff /etc/default
  sudo cp ~/work/etc/default/udp-weather-mon /etc/default
  sudo cp ~/work/etc/systemd/system/switch-to-poweroff.service /etc/systemd/system
  sudo cp ~/work/etc/systemd/system/udp-weather-mon.service /etc/systemd/system
  sudo systemctl enable udp-weather-mon.service
  sudo systemctl enable switch-to-poweroff.service
}

echo "Done."
