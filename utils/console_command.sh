#!/bin/bash

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <command>"
  exit 1
fi

# Get the command from the argument
COMMAND="$1"

# Echo the command before executing it
echo "Executing console command: $COMMAND"

# Access the OpenHAB console and execute the provided command
sudo docker exec -i openhab /bin/bash /openhab/runtime/bin/client -u openhab -p habopen <<EOF
$COMMAND
EOF

# Check if the command execution was successful
if [ $? -eq 0 ]; then
  echo "Command successfully executed."
else
  echo "Failed to execute the command."
fi