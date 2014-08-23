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
CURRENT_DIR=$(dirname $(readlink -f $0))
BASE_DIR=$(dirname ${CURRENT_DIR})
CLUSTER_DIR=${BASE_DIR}/clusters/${CLUSTER_NAME}

if [ ! -d ${CLUSTER_DIR} ]
then
	echo "cluster named ${CLUSTER_NAME} does not exist."
	exit 1
fi

cp /etc/hosts ${CLUSTER_DIR}/public-hosts

${PYTHON} ${CURRENT_DIR}/update_registry.py remove -r ${CLUSTER_DIR}/registry -n ${HOSTNAME} -s ${CLUSTER_DIR}/public-hosts -t ${CLUSTER_DIR}/private-hosts

sudo mv ${CLUSTER_DIR}/public-hosts /etc/hosts
sudo service nscd restart

# remove ssh fingerprint
PUBLIC_IP=$(getent hosts ${HOSTNAME} | awk '{print $1}')
ssh-keygen -R ${PUBLIC_IP} -f "${HOME}/.ssh/known_hosts"
ssh-keygen -R ${HOSTNAME} -f "${HOME}/.ssh/known_hosts"
