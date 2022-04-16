#!/bin/bash

readonly SCRIPT_NAME=${0##*/}

print_help()
{
   cat << END
Usage: $SCRIP_NAME OPTIONS
Execute GetCSVFromWeather.py OPTIONS

--device-name: Required 'ESP module device name'
--date-from: Optional SQL Criteria Start date in t_weahter.
--date-to: Optional SQL Criteria End date in t_weahter.
--help	display this help and exit

Example:
[short options]
  $SCRIPT_NAME -d esp8266_1 -f 2021-08-01 -t 2021-09-30
  $SCRIPT_NAME -d esp8266_1
[long options]
  $SCRIPT_NAME --device-name esp8266_1 --date-from 2021-08-01 --date-to 2021-09-30 --without-header --with-device-csv
  $SCRIPT_NAME --device-name esp8266_1 --date-from 2021-08-01 --date-to 2021-09-30 --with-device-csv
  $SCRIPT_NAME --device-name esp8266_1 --date-from 2021-08-01 --date-to 2021-09-30 --without-header
  $SCRIPT_NAME --device-name esp8266_1 --date-from 2021-08-01 --date-to 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1 --date-from 2021-08-01
  $SCRIPT_NAME --device-name esp8266_1 --date-to 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1
END
}

print_error()
{
   cat << END 1>&2
$SCRIPT_NAME: $1
Try --help option
END
}

params=$(getopt -n "$SCRIPT_NAME" \
       -o d:f:t:\
       -l device-name: -l date-from: -l date-to: -l without-header -l with-device-csv -l help \
       -- "$@")

# Check command status: $?
if [[ $? -ne 0 ]]; then
  echo 'Try --help option for more information' 1>&2
  exit 1
fi

eval set -- "$params"

device_name=
date_from=
date_to=
without_header=
with_device_csv=

# Parse options
# Positional parameter count: $#
while [[ $# -gt 0 ]]
do
  case "$1" in
    -d | --device-name)
      device_name=$2
      shift 2
      ;;
    -f | --date-from)
      date_from=$2
      shift 2
      ;;
    -t | --date-to)
      to_date=$2
      shift 2
      ;;
    --without-header)
      without_header='--without-header'
      shift
      ;;
    --with-device-csv)
      with_device_csv='--with-device-csv'
      shift
      ;;
    --help)
      print_help
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Internal Error"
      exit 1
      ;;
  esac
done

echo "$SCRIPT_NAME --device-name $device_name --date-from $date_from --date-to $date_to $without_header $with_device_csv"

# Check required option: --device-name
if [ -z $device_name ]; then
  print_error "Required --device-name xxxxx"
  exit 1
fi

option_date_from=
if [ -n "$date_from" ]; then
  option_date_from="--date-from $date_from"
fi
option_date_to=
if [ -n "$to_date" ]; then
  option_date_to="--date-to $to_date"
fi

echo "pigpio/GetCSVFromWeather.py --device-name $device_name $option_date_from $option_date_to"

. ~/py_venv/py37_pigpio/bin/activate

python pigpio/GetCSVFromWeather.py --device-name $device_name $option_date_from $option_date_to $without_header $with_device_csv

deactivate
