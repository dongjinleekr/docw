#!/bin/bash

set -e

# help
if [ $# -eq 8 ]
then
  CLIENT_ID=$1
	API_KEY=$2
	REGION=$3
	CLUSTER_NAME=$4
	HOSTNAME=$5
	EMAIL_SERVER=$6
	EMAIL_USERNAME=$7
	EMAIL_PASSWORD=$8
else
	echo "Usage: $0 {do-client-id} {do-api-key} {region(sgp1|nyc2)} {cluster-name} {hostname} {email-server} {email-account} {email-password}"
	exit 1
fi

PYTHON=$(which python3)
SBIN_DIR=$(dirname $(readlink -f $0))
BASE_DIR=$(dirname ${SBIN_DIR})

. ${SBIN_DIR}/functions.sh

register_node $@
