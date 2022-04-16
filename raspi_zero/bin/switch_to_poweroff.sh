#!/bin/bash

. /home/pi/py_venv/py37_pigpio/bin/activate

python /home/pi/bin/pigpio/SwitchToPoweroff.py --poweroff-pin $1 --ledblink-pin $2

deactivate
