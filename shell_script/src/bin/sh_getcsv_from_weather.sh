#!/bin/bash

readonly SCRIPT_NAME=${0##*/}

PATH_EXPORT_CSV="$HOME/Downloads/csv"
PREFIX_CSV_NAME="weather_"
DEVICE_CSV_NAME="device.csv"

print_help()
{
   cat << END
Usage: $SCRIP_NAME OPTIONS
Execute GetCSVFromWeather.py OPTIONS

--device-name: ESP module device name is Required.
--from-date: SQL Criteria Start date in t_weahter is optional.
--to-date: SQL Criteria End date in t_weahter is optional.
--output-device-csv: Output device.csv in t_device is optional.
--help	display this help and exit

Example:
1.Output weather csv
  $SCRIPT_NAME --device-name esp8266_1 --device espxxxx --from-date 2021-08-01 --to-date 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1 --device espxxxx --from-date 2021-08-01
  $SCRIPT_NAME --device-name esp8266_1 --device espxxxx --to-date 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1 --device espxxxx
  $SCRIPT_NAME --device-name esp8266_1 -d espxxxx -f 2021-08-01 -t 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1 -d espxxxx -f 2021-08-01
  $SCRIPT_NAME --device-name esp8266_1 -d espxxxx -t 2021-09-30
  $SCRIPT_NAME --device-name esp8266_1 -d espxxxx

2.Output device csv:
  $SCRIPT_NAME --output-device-csv
END
}

print_error()
{
   cat << END 1>&2
$SCRIPT_NAME: $1
Try --help option
END
}

query() {
   sqlite3 -cmd 'PRAGMA foreign_key=ON' "$PATH_WEATHER_DB" "$@"
}

next_to_date() {
    retval=$(date -d "$1 1 days" +'%F');
    echo "$retval"
}

# YYYYmmdd
suffix_datetime() {
    retval=$(date +'%Y%m%d');
    echo "$retval"
}

get_device_csv() {
cat<<-EOF | query -csv
    SELECT * FROM t_device ORDER BY id;
EOF
}

get_csv() {
    dev_name="$1";
    where="$2";
    # echo "dev_name: ${dev_name}"
    # echo "where: ${where}"
cat<<-EOF | query -csv
    SELECT
      did,
      datetime(measurement_time, 'unixepoch', 'localtime'), 
      temp_out, temp_in, humid, pressure
    FROM
      t_weather wh INNER JOIN t_device dv ON wh.did = dv.id
    WHERE
      dv.name='${dev_name}' AND (${where})
    ORDER BY measurement_time;
EOF
}

params=$(getopt -n "$SCRIPT_NAME" \
       -o d:f:t: \
       -l device-name: -l from-date: -l to-date: -l output-device-csv -l help \
       -- "$@")

# Check command exit status
if [[ $? -ne 0 ]]; then
  echo 'Try --help option for more information' 1>&2
  exit 1
fi
eval set -- "$params"

# init option value
device_name=
from_date=
to_date=
output_device_csv=false

# Parse options
# Positional parameter count: $#
while [[ $# -gt 0 ]]
do
  case "$1" in
    -d | --device-name)
      device_name=$2
      shift 2
      ;;
    -f |--from-date)
      from_date=$2
      shift 2
      ;;
    -t | --to-date)
      to_date=$2
      shift 2
      ;;
    --output-device-csv)
      output_device_csv=true
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
  esac
done

if [[ $output_device_csv == true ]]; then
   echo '"id","name"' > "$PATH_EXPORT_CSV/$DEVICE_CSV_NAME"
   get_device_csv >> "$PATH_EXPORT_CSV/$DEVICE_CSV_NAME"
   if [ $? = 0 ]; then
      echo "Output device csv to $PATH_EXPORT_CSV/$DEVICE_CSV_NAME"
      row_count=$(cat "${PATH_EXPORT_CSV}/${DEVICE_CSV_NAME}" | wc -l)
      row_count=$(( row_count - 1))
      echo "Device record count: ${row_count}" 
   fi
   exit 0   
fi

echo "$SCRIPT_NAME --device-name $device_name --from-date $from_date --to-date $to_date"

# Check required option: --device-name
if [ -z "$device_name" ]; then
  print_error "Required --device-name xxxxx"
  exit 1
fi

where=
filename="${PREFIX_CSV_NAME}${device_name}_"
if [ -n "$from_date" ] && [ -n "$to_date" ]; then
   next_date=$(next_to_date "$to_date");
   where=" measurement_time >= strftime('%s','"$from_date"','-9 hours') AND measurement_time < strftime('%s','"$next_date"','-9 hours')"
   range_from=$(echo "${from_date}" | sed 's/-//g') 
   range_to=$(echo "${to_date}" | sed 's/-//g') 
   filename="${filename}${range_from}-${range_to}"
fi
if [ -n "$from_date" ] && [ -z "$to_date" ]; then
   where=" measurement_time >= strftime('%s','"$from_date"','-9 hours')"
   range=$(echo "${from_date}" | sed 's/-//g') 
   filename="${filename}${range}"
fi
if [ -z "$from_date" ] && [ -n "$to_date" ]; then
   next_date=$(next_to_date "$to_date");
   where=" measurement_time < strftime('%s','"$next_date"','-9 hours')"
   range=$(echo "${to_date}" | sed 's/-//g') 
   filename="${filename}${range}"
fi
if [ -z "$from_date" ] && [ -z "$to_date" ]; then
   where=" 1=1"
   filename="${filename}_all"
fi
date_part=$(suffix_datetime)
filename="${filename}_${date_part}.csv"

header='"did","measurement_time","temp_out","temp_in","humid","pressure"'
echo $header > "$PATH_EXPORT_CSV/$filename"
get_csv "$device_name" "$where" >> "$PATH_EXPORT_CSV/$filename"
if [ $? = 0 ]; then
   echo "Output weather csv to $PATH_EXPORT_CSV/$filename"
   row_count=$(cat "${PATH_EXPORT_CSV}/${filename}" | wc -l)
   row_count=$(( row_count - 1))
   echo "Weather record count: ${row_count}" 
fi   

