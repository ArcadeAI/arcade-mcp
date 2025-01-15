#!/bin/bash

# Get all directories and format as JSON array
echo -n '['
ls -d toolkits/*/ | cut -d'/' -f2 | sort -u | awk '{
    if (NR==1) {
        printf "\"%s\"", $0
    } else {
        printf ", \"%s\"", $0
    }
}'
echo ']'
