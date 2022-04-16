#!/bin/bash

# ./start.sh                    -> development
# ./start.sh prod | production  ->production
env_mode="development"
if [ $# -eq 0 ]; then
    :
else
   if [[ "$1" = "prod" || "$1" = "production" ]]; then 
        env_mode="production"
   fi
fi

# Hostname is not resolved when this service starts (systemd-hostname.service)
#ip_host=$(/bin/hostname -I | awk '{ print $1 }')
#name_in_hosts=$(/bin/cat /etc/hosts | grep $ip_host | awk '{ print $2 }')
# /etc/hosts in following line
# xxx.xxx.xxx.xx myhost.local myhost -> myhost.local
host_name="$(/bin/cat /etc/hostname)"
export IP_HOST="${host_name}.local"
export ENV=$env_mode
echo "$IP_HOST with $ENV"

EXEC_PATH=
if [ -n "$PATH_WEBAPP" ]; then
   EXEC_PATH=$PATH_WEBAPP
else
   EXEC_PATH=$HOME/webapp
fi

. $HOME/py_venv/py37_webapp/bin/activate
python $EXEC_PATH/run.py

deactivate
