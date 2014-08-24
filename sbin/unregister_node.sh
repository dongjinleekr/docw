#!/bin/bash

set -e

# help
if [ $# -eq 2 ]
then
	CLUSTER_NAME=$1
	HOSTNAME=$2
else
	echo "Usage: $0 {cluster-name} {hostname}"
	exit 1
fi

PYTHON=$(which python3)
SBIN_DIR=$(dirname $(readlink -f $0))
BASE_DIR=$(dirname ${SBIN_DIR})

. ${SBIN_DIR}/functions.sh

unregister_node $@
