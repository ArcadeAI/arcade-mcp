#!/bin/bash

WORKERS=${WORKERS:-1}

echo "Starting arcade..."
arcade serve --host $HOST --port $PORT --workers $WORKERS $([ "$OTEL_ENABLE" = "true" ] && echo "--otel-enable")
