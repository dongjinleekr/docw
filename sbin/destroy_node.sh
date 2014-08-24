#!/bin/bash

set -e

# help
if [ $# -eq 3 ]
then
	CLIENT_ID=$1
	API_KEY=$2
	HOSTNAME=$3
else
	echo "Usage: $0 {do-client-id} {do-api-key} {hostname}"
	exit 1
fi

PYTHON=$(which python3)
SBIN_DIR=$(dirname $(readlink -f $0))

. ${SBIN_DIR}/functions.sh

destroy_node $@
