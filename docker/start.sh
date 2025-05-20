#!/bin/bash

echo "Starting arcade..."
arcade serve --host $HOST --port $PORT $([ "$OTEL_ENABLE" = "true" ] && echo "--otel-enable")
