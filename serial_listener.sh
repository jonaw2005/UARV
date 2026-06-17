#!/bin/bash

PORT="/dev/ttyAMA0"
BAUD="57600"

echo "Listening on $PORT at $BAUD ... (CTRL+C to stop)"

# Port konfigurieren
stty -F $PORT $BAUD raw -echo -icanon -parenb cs8 -cstopb

# Endlosschleife lesen
while true; do
    if read -r -t 1 line < $PORT; then
        echo "$line"
    fi
done