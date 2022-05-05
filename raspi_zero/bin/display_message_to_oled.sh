#!/bin/bash

readonly SCRIPT_NAME=${0##*/}

params=$(getopt -n "$SCRIPT_NAME" \
       -o '' \
       -l encoded-message: -l has-list \
       -- "$@")

eval set -- "$params"

# Required
message=
# Optional
has_list=

while [[ $# -gt 0 ]]
do
  case "$1" in
    --encoded-message)
      message=$2
      shift 2
      ;;
    --has-list)
      has_list='--has-list'
      shift
      ;;
    --)
      shift
      break
      ;;
  esac
done

echo "$SCRIPT_NAME --encoded-message $message $has_list"

if [[ -z "$message" ]]; then
  echo "--encoded-message xxxxxxx is required!"
  exit 1
fi

. ~/py_venv/py37_pigpio/bin/activate

python $HOME/bin/pigpio/DisplayMessageToOLED.py --encoded-message $message $has_list

deactivate
