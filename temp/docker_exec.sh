#!/usr/bin/expect -f
set password "habopen"
spawn sudo docker exec -it openhab /openhab/runtime/bin/client
expect "Password:"
send "$password\r"
interact