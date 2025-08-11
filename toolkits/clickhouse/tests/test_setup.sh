#!/bin/bash

docker run -d --name some-clickhouse-server --ulimit nofile=262144:262144 -p 8123:8123 -p 8443:8443 -p 9000:9000 yandex/clickhouse-server
