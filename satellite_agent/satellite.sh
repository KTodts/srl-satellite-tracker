#!/bin/bash
###########################################################################
# Description:
#     This script will launch the python script of satellite_agent
#     (forwarding any arguments passed to this script).
#
# Copyright (c) 2018 Nokia
###########################################################################

#!/bin/bash

_term (){
    echo "Caught signal SIGTERM !! "
    # when SIGTERM is caught: kill the child process
    kill -TERM "$child" 2>/dev/null
}

# associate a handler with signal SIGTERM
trap _term SIGTERM

# set local variables
virtual_env="/opt/srlinux/python/virtual-env/bin/activate"
main_module="/etc/opt/srlinux/appmgr/satellite_agent/satellite.py"

# start python virtual environment, which is used to ensure the correct python packages are installed and the correct python version is used
source "${virtual_env}"

# update PYTHONPATH variable with the agent directory and the SR Linux gRPC
export  PYTHONPATH="$PYTHONPATH:/etc/opt/srlinux/helper:/etc/opt/srlinux/appmgr/satellite_agent:/opt/srlinux/bin:/usr/lib/python3.6/site-packages/sdk_protos"

# start the agent in the background (as a child process)
python3 ${main_module} &

# save its process id
child=$!

# wait for the child process to finish
wait "$child"
