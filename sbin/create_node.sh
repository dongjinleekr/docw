#!/bin/bash

set -e

# help
if [ $# -eq 9 ]
then
	CLIENT_ID=$1
	API_KEY=$2
	HOSTNAME=$3
	SIZE_ID=$4
	IMAGE=$5
	REGION=$6
	EMAIL_SERVER=$7
	EMAIL_USERNAME=$8
	EMAIL_PASSWORD=$9
else
	echo "Usage: $0 {do-client-id} {do-api-key} {hostname} {do-size-id} {image(ubuntu-14.04)} {region(sgp1|nyc2)} {email-server} {email-account} {email-password}"
	exit 1
fi

PYTHON=$(which python3)
CURRENT_DIR=$(dirname $(readlink -f $0))
ROOT_PASSWORD='root_password'

# create nodes
RESULT=$(${PYTHON} ${CURRENT_DIR}/create.py -c ${CLIENT_ID} -a ${API_KEY} -n ${HOSTNAME} -s ${SIZE_ID} -i ${IMAGE} -r ${REGION})

TOKENS=( ${RESULT} ); 

PUBLIC_IP=${TOKENS[0]}
PRIVATE_IP=${TOKENS[1]}

TMP_PASSWORD=$(${PYTHON} ${CURRENT_DIR}/fetchmail.py -s ${EMAIL_SERVER} -u ${EMAIL_USERNAME} -p ${EMAIL_PASSWORD} -n ${HOSTNAME})

ssh-keygen -R ${PUBLIC_IP} -f "${HOME}/.ssh/known_hosts" >> /dev/null 2>&1

${CURRENT_DIR}/init-${REGION}.ex ${PUBLIC_IP} ${TMP_PASSWORD} ${ROOT_PASSWORD} >> /dev/null 2>&1
