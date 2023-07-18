#!/bin/bash

status=$(sudo docker exec -it openhab /openhab/runtime/bin/status)

echo $status

if [[ ("$status" == *"Running ..."*) && ("$status" != *"Not Running ..."*)]]; then
  echo "Running."
else
  echo "Not Running."
fi