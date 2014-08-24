#!/bin/bash

set -e

# help
if [ $# -eq 6 ]
then
	CLIENT_ID=$1
	API_KEY=$2
	HOSTNAME=$3
	SIZE_ID=$4
	OS_IMAGE=$5
	REGION=$6
else
	echo "Usage: $0 {do-client-id} {do-api-key} {hostname} {do-size-id} {os-image(ubuntu-14.04)} {region(sgp1|nyc2)}"
	exit 1
fi

PYTHON=$(which python3)
SBIN_DIR=$(dirname $(readlink -f $0))

. ${SBIN_DIR}/functions.sh

create_node $@
