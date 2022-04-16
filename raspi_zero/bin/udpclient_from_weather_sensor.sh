#!/bin/bash

. /home/pi/py_venv/py37_pigpio/bin/activate

# udp_weather_mon.service
# ExecStart~/home/pi/bin/udpclint_from_weather_sehsor.sh $UDP_PORT $BRIGHTNESS_PIN
# --udp-port 2222 --brightness-pin 17
python /home/pi/bin/pigpio/UDPClientFromWeatherSensor.py --udp-port $1 --brightness-pin $2

deactivate
