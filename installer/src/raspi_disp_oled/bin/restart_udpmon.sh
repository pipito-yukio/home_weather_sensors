#!/bin/bash

my_passwd=papayukio%5588
echo $my_passwd | {
   sudo --stdin systemctl stop udp-weather-mon.service
   sudo systemctl start udp-weather-mon.service
}
