#!/bin/bash

echo "Installing toolkits..."
for toolkit in $(echo $TOOLKITS | tr "," " "); do
    echo "Installing $toolkit..."
    pip install $toolkit
done

echo "Starting arcade..."
arcade workerup --host $HOST --port $PORT $([ "$OTEL_ENABLE" = "true" ] && echo "--otel-enable")
