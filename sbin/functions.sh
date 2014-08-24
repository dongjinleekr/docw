# all functions in this script requires following varaibles:
# SBIN_DIR : 
# BASE_DIR : 
# PYTHON : 

ROOT_PASSWORD='root_password'
	
# create node
create_node() {
  CLIENT_ID=$1
	API_KEY=$2
	HOSTNAME=$3
	SIZE_ID=$4
	OS_IMAGE=$5
	REGION=$6

	# create node
	${PYTHON} ${SBIN_DIR}/create.py -c ${CLIENT_ID} -a ${API_KEY} -n ${HOSTNAME} -s ${SIZE_ID} -i ${OS_IMAGE} -r ${REGION}
}

# register node
register_node() {
  CLIENT_ID=$1
	API_KEY=$2
	REGION=$3
	CLUSTER_NAME=$4
	HOSTNAME=$5
	EMAIL_SERVER=$6
	EMAIL_USERNAME=$7
	EMAIL_PASSWORD=$8

	# acquire ip address
	RESULT=$(${PYTHON} ${SBIN_DIR}/inspect.py -c ${CLIENT_ID} -a ${API_KEY} -n ${HOSTNAME})
	TOKENS=( ${RESULT} );
	PUBLIC_IP=${TOKENS[0]}
	PRIVATE_IP=${TOKENS[1]}

	ssh-keygen -R ${PUBLIC_IP} -f "${HOME}/.ssh/known_hosts" > /dev/null 2>&1

	# acquire temporary password
	TMP_PASSWORD=$(${PYTHON} ${SBIN_DIR}/fetchmail.py -s ${EMAIL_SERVER} -u ${EMAIL_USERNAME} -p ${EMAIL_PASSWORD} -n ${HOSTNAME})

	# reset password
	${SBIN_DIR}/init-${REGION}.ex ${PUBLIC_IP} ${TMP_PASSWORD} ${ROOT_PASSWORD} > /dev/null 2>&1

	# update registry file
	REGISTRY_PATH=${BASE_DIR}/registry
	PRIVATE_HOSTS_PATH=${BASE_DIR}/private-hosts
	PUBLIC_HOSTS_PATH=${BASE_DIR}/public-hosts
	
	if [ ! -f ${REGISTRY_PATH} ]
	then
		touch ${REGISTRY_PATH}
	fi

	touch ${PRIVATE_HOSTS_PATH}
	cp /etc/hosts ${PUBLIC_HOSTS_PATH}

	${PYTHON} ${SBIN_DIR}/update_registry.py add -r ${REGISTRY_PATH} -c ${CLUSTER_NAME} -n ${HOSTNAME} -s ${PUBLIC_HOSTS_PATH} -t ${PRIVATE_HOSTS_PATH} -u ${PUBLIC_IP} -v ${PRIVATE_IP}

	sudo mv ${PUBLIC_HOSTS_PATH} /etc/hosts
	sudo service nscd restart > /dev/null 2>&1

	# add ssh fingerprint
	ssh-add ${HOME}/.ssh/id_rsa > /dev/null 2>&1

	${SBIN_DIR}/copy-ssh-first.ex ${HOME}/.ssh/id_rsa.pub ${HOSTNAME} root ${ROOT_PASSWORD} > /dev/null 2>&1

	ssh-keyscan -H ${PUBLIC_IP} >> ~/.ssh/known_hosts
	ssh-keyscan -H ${HOSTNAME} >> ~/.ssh/known_hosts
}

# unregister node
unregister_node() {
	CLUSTER_NAME=$1
	HOSTNAME=$2

	# remove ssh fingerprint
	PUBLIC_IP=$(getent hosts ${HOSTNAME} | awk '{print $1}')
	ssh-keygen -R ${PUBLIC_IP}
	ssh-keygen -R ${HOSTNAME}

	# update registry file
	REGISTRY_PATH=${BASE_DIR}/registry
	PRIVATE_HOSTS_PATH=${BASE_DIR}/private-hosts
	PUBLIC_HOSTS_PATH=${BASE_DIR}/public-hosts
	
	if [ ! -f ${REGISTRY_PATH} ]
	then
		echo "registry file does not exist."
		exit 1
	fi

	cp /etc/hosts ${PUBLIC_HOSTS_PATH}

	${PYTHON} ${SBIN_DIR}/update_registry.py remove -r ${REGISTRY_PATH} -n ${HOSTNAME} -s ${PUBLIC_HOSTS_PATH} -t ${PRIVATE_HOSTS_PATH}

	sudo mv ${PUBLIC_HOSTS_PATH} /etc/hosts
	sudo service nscd restart > /dev/null 2>&1
}

# destroy node
destroy_node() {
	CLIENT_ID=$1
	API_KEY=$2
	HOSTNAME=$3
	
	${PYTHON} ${SBIN_DIR}/destroy.py -c ${CLIENT_ID} -k ${API_KEY} -n ${HOSTNAME}
}
