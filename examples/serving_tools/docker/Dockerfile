ARG VERSION=latest

# Base worker image
FROM ghcr.io/arcadeai/worker-base:${VERSION}

# Copy requirements and constraints
COPY toolkits.txt ./

# Install toolkits from file
RUN pip install -r toolkits.txt
