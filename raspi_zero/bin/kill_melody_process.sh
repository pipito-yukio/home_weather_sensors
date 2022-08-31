#!/bin/bash

bak_ifs=$IFS
IFS=

for ps_line in $(ps aux | grep PlayMelody | grep -v grep)
do
   echo $ps_line | awk '{ print $2 }' | xargs kill
done

IFS=$bak_ifs

