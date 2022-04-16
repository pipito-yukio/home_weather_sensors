#!/bin/bash

. ~/py_venv/py37_pigpio/bin/activate

# --baudrate [9600 or 115200]
python pigpio/SerialMonitor.py --baudrate $1

deactivate
