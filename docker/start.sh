#!/bin/bash

echo "Starting arcade..."
arcade workerup --host $HOST --port $PORT $([ "$OTEL_ENABLE" = "true" ] && echo "--otel-enable")
