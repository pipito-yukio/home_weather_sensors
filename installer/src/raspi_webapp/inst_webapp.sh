#!/bin/bash

# execute before export my_passwd=xxxxxx

# Add webapp host in hosts
ip_addr=$(ifconfig eth0 | grep "inet " | awk '{ print $2 }')
local_host=$(cat /etc/hosts | grep 127.0.1.1 | awk '{ print $2 }')
local_host="${local_host}.local"
add_host="${ip_addr}		${local_host}"
echo $my_passwd | { sudo --stdin chown pi.pi /etc/hosts
  sudo echo $add_host>>/etc/hosts
  sudo chown root.root /etc/hosts
}

# Create Virtual Python environment.
cd py_venv
python3 -m venv py37_webapp
. py37_webapp/bin/activate
pip install -U pip
pip install -r ~/work/py_venv/requirements_webapp.txt
deactivate
cd ~/

# make soft link db
cd webapp/weather_finder
ln -s ~/bin/pigpio/db db
cd ~/

# Enable webapp service
echo $my_passwd | { sudo --stdin cp ~/work/etc/systemd/system/webapp-weather-finder.service /etc/systemd/system
  sudo systemctl enable webapp-weather-finder.service
}

echo "Done."

echo $my_passwd | sudo --stdin reboot

