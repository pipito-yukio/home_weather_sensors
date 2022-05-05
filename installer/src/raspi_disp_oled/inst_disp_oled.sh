#!/bin/bash

# add application environ values to .bashrc
# PATH_DATAS=$HOME/datas
cat ~/work/add_env_in_bashrc.txt >> ~/.bashrc

# execute before export my_passwd=xxxxxx

echo $my_passwd | sudo --stdin apt update && sudo apt -y upgrade
# install IPA-font, other system libraries
echo $my_passwd | sudo --stdin apt -y install fonts-ipafont libopenjp2*

# Add luma LCD, OLED libraries.
cd py_venv
. py37_pigpio/bin/activate
pip install luma.core luma.lcd luma.oled
deactivate
cd ~/

# Copy crontab file & reload cron/ Enable system service
echo $my_passwd | { sudo --stdin cp ~/work/crontab/pi /var/spool/cron/crontabs
  sudo service cron reload
  sudo cp ~/work/etc/systemd/system/button_start.service /etc/systemd/system
  sudo systemctl enable button_start.service
}

echo "Done!"
echo "Please sudo reboot."
