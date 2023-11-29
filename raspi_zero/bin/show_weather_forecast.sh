#!/bin/bash

. $HOME/py_venv/py37_pigpio/bin/activate
python $HOME/bin/pigpio/ShowWeatherForecast.py

deactivate
