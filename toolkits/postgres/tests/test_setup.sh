#!/bin/bash

# Run PostgreSQL container
docker run -d --name some-postgres-server -e POSTGRES_HOST_AUTH_METHOD=trust -p 5432:5432 postgres:latest

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if docker exec some-postgres-server pg_isready -U postgres > /dev/null 2>&1; then
    echo "PostgreSQL is ready!"
    break
  fi
  echo "Waiting... ($i/30)"
  sleep 1
done
