#!/bin/bash

readonly SCRIPT_NAME=${0##*/}

print_help()
{
   cat << END
Usage: $SCRIP_NAME OPTIONS
Execute tkinter_plot_weather_csv.py OPTIONS

--csv-path: open csv filename, optinal.
--help	display this help and exit

Example:
  $SCRIPT_NAME --csv-path ~/Downloads/csv/weather_esp8266_1_xxxx.csv
  $SCRIPT_NAME
END
}

print_error()
{
   cat << END 1>&2
$SCRIPT_NAME: $1
Try --help option
END
}

params=$(getopt -n "$SCRIPT_NAME" -o '' -l csv-path: -l help -- "$@")

# Check command status: $?
if [[ $? -ne 0 ]]; then
  echo 'Try --help option for more information' 1>&2
  exit 1
fi

eval set -- "$params"

csv_path=

# Parse options
# Positional parameter count: $#
while [[ $# -gt 0 ]]
do
  case "$1" in
    --csv-path)
      csv_path=$2
      shift 2
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

opt_csv_path=
if [ -n "$csv_path" ]; then
  opt_csv_path="--csv-path $csv_path"
fi

. ~/py_venv/py37_learn_matplotlib/bin/activate

python TkinterPlotWeatherCsv.py $opt_csv_path

deactivate