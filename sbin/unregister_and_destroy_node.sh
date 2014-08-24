#!/bin/bash

set -e

# help
if [ $# -eq 4 ]
then
	CLIENT_ID=$1
	API_KEY=$2
	CLUSTERNAME=$3
	HOSTNAME=$4
else
	echo "Usage: $0 {do-client-id} {do-api-key} {clustername} {hostname}"
	exit 1
fi

PYTHON=$(which python3)
SBIN_DIR=$(dirname $(readlink -f $0))
BASE_DIR=$(dirname ${SBIN_DIR})

. ${SBIN_DIR}/functions.sh

unregister_node ${CLUSTERNAME} ${HOSTNAME}
destroy_node ${CLIENT_ID} ${API_KEY} ${HOSTNAME}
