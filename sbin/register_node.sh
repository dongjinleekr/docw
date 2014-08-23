#!/bin/bash

set -e

# help
if [ $# -eq 4 ]
then
	CLUSTER_NAME=$1
	HOSTNAME=$2
	PUBLIC_IP=$3
	PRIVATE_IP=$4
else
	echo "Usage: $0 {cluster-name} {hostname} {public-ip} {private-ip}"
	exit 1
fi

PYTHON=$(which python3)
CURRENT_DIR=$(dirname $(readlink -f $0))
BASE_DIR=$(dirname ${CURRENT_DIR})
CLUSTER_DIR=${BASE_DIR}/clusters/${CLUSTER_NAME}
ROOT_PASSWORD='root_password'

if [ ! -d ${CLUSTER_DIR} ]
then
	mkdir -p ${CLUSTER_DIR}
	touch ${CLUSTER_DIR}/registry
	touch ${CLUSTER_DIR}/private-hosts
fi

cp /etc/hosts ${CLUSTER_DIR}/public-hosts

${PYTHON} ${CURRENT_DIR}/update_registry.py add -r ${CLUSTER_DIR}/registry -n ${HOSTNAME} -s ${CLUSTER_DIR}/public-hosts -t ${CLUSTER_DIR}/private-hosts -u ${PUBLIC_IP} -v ${PRIVATE_IP}

sudo mv ${CLUSTER_DIR}/public-hosts /etc/hosts
sudo service nscd restart

# add ssh fingerprint
ssh-add ${HOME}/.ssh/id_rsa

${CLUSTER_DIR}/copy-ssh-first.ex ${HOME}/.ssh/id_rsa.pub ${HOSTNAME} root ${ROOT_PASSWORD}

ssh-keyscan -H ${PUBLIC_IP} >> ~/.ssh/known_hosts
ssh-keyscan -H ${HOSTNAME} >> ~/.ssh/known_hosts