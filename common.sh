# exe
PYTHON=$(which python3)

# settings file
SETTINGS_DIR=${HOME}/.docw
REGISTRY_PATH=${SETTINGS_DIR}/registry
ID_SEQUENCE_PATH=${SETTINGS_DIR}/sequence
CFG_PATH=${SETTINGS_DIR}/config.cfg

[ -d "${SETTINGS_DIR}" ] || mkdir ${SETTINGS_DIR}
[ -f "${REGISTRY_PATH}" ] || echo '{ "entries": [] }' > ${REGISTRY_PATH}
[ -f "${ID_SEQUENCE_PATH}" ] || echo '0' > ${ID_SEQUENCE_PATH}
[ -f "${CFG_PATH}" ] || { echo 'config.cfg missing!!'; exit 1 ; }

. ${CFG_PATH}

BASE_DIR=$(dirname $(dirname $(readlink -f $0)))
SBIN_DIR=${BASE_DIR}/sbin
TEMPLATE_DIR=${BASE_DIR}/templates
WORKING_DIR=${BASE_DIR}

# constants
ROOT_PASSWORD='root_password'
REMOTE_HOST_USER='hduser'
REMOTE_HOST_PASSWD='hduser'
HADOOP_VERSION=1.2.1
SNAPPY_VERSION=1.1.1

# wait all
wait_all() {
	${PYTHON} - $@ << 'EOF'
#!/usr/bin/python3

import sys, psutil

def main():
	waitfor = set([ int(pid) for pid in sys.argv[1:] ])

	while waitfor:
		waitfor.intersection_update(set(psutil.get_pid_list()))

	return 0;

if __name__ == "__main__":
	sys.exit(main())
EOF
}

# add host
add_host() {
	HOSTNAME=$1
	SIZE=$2

	# create node
	${PYTHON} ${SBIN_DIR}/create.py -c ${CLIENT_ID} -a ${API_KEY} -n ${HOSTNAME} -s ${SIZE} -i ${OS_IMAGE} -r ${REGION}
	
	# add to register
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} add host ${HOSTNAME} ${SIZE}
}

# add cluster
add_cluster() {
	CLUSTER_NAME=$1
	ROLE=$2
	
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} add cluster ${CLUSTER_NAME} ${ROLE}
}

# add host to namespace
assign_to_namespace() {
	NAMESPACE_NAME=$1
	HOSTNAME=$2
	
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} assign namespace ${NAMESPACE_NAME} ${HOSTNAME}
}

# add host to cluster
assign_to_cluster() {
	CLUSTER_NAME=$1
	HOSTNAME=$2
	
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} assign cluster ${CLUSTER_NAME} ${HOSTNAME}
}

update_namespace_hosts() {
	NAMESPACE_NAME=$1
	
	HOSTS_PATH=$(mktemp)
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} generate private ${HOSTS_PATH} ${NAMESPACE_NAME}
	
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list namespace ${NAMESPACE_NAME})
	HOSTNAMES=( ${RESULT} )
	
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		# update /etc/hosts
		scp ${HOSTS_PATH} root@${HOSTNAME}:/etc/hosts # > /dev/null 2>&1
		ssh -n root@${HOSTNAME} 'service nscd restart' # > /dev/null 2>&1
	done
}

# 
display_all_clusters_info() {
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} display --all
}

#
display_cluster_info() {
	CLUSTER_NAME=$1
	
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} display ${CLUSTER_NAME}
}

# 
assign_ip_address() {
	HOSTNAME=$1

	CURRENT_HOSTS_PATH=$(mktemp)
	REGISTERED_HOSTS_PATH=$(mktemp)
	UPDATED_HOSTS_PATH=$(mktemp)
	
	# get /etc/hosts entries which are not in registry. note: can be abstracted.
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} generate public ${REGISTERED_HOSTS_PATH}
	cp /etc/hosts ${CURRENT_HOSTS_PATH}
	grep -F -x -v -f ${REGISTERED_HOSTS_PATH} ${CURRENT_HOSTS_PATH} > ${UPDATED_HOSTS_PATH}
	CURRENT_HOSTS_PATH=${UPDATED_HOSTS_PATH}

	# acquire ip address
	RESULT=$(${PYTHON} ${SBIN_DIR}/inspect.py ${CLIENT_ID} ${API_KEY} ${HOSTNAME})
	TOKENS=( ${RESULT} )
	PUBLIC_IP=${TOKENS[0]}
	PRIVATE_IP=${TOKENS[1]}

	ssh-keygen -R ${PUBLIC_IP} -f "${HOME}/.ssh/known_hosts" > /dev/null 2>&1

	# acquire temporary password
	TMP_PASSWORD=$(${PYTHON} ${SBIN_DIR}/fetchmail.py -s ${EMAIL_SERVER} -u ${EMAIL_USERNAME} -p ${EMAIL_PASSWORD} -n ${HOSTNAME})

	# reset password
	${SBIN_DIR}/init-${REGION}.ex ${PUBLIC_IP} ${TMP_PASSWORD} ${ROOT_PASSWORD} > /dev/null 2>&1

	# add to registry
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} assign address ${HOSTNAME} ${PUBLIC_IP} ${PRIVATE_IP}

	# update /etc/hosts. note: can be abstracted.
	REGISTERED_HOSTS_PATH=$(mktemp)
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} generate public ${REGISTERED_HOSTS_PATH}
	cat ${REGISTERED_HOSTS_PATH} >> ${CURRENT_HOSTS_PATH}
	sudo cp ${CURRENT_HOSTS_PATH} /etc/hosts

	sudo service nscd restart > /dev/null 2>&1

	# add ssh fingerprint (root)
	ssh-add ${HOME}/.ssh/id_rsa > /dev/null 2>&1

	${SBIN_DIR}/copy-ssh-first.ex ${HOME}/.ssh/id_rsa.pub ${HOSTNAME} root ${ROOT_PASSWORD} > /dev/null 2>&1

	ssh-keyscan -H ${PUBLIC_IP} >> ~/.ssh/known_hosts
	ssh-keyscan -H ${HOSTNAME} >> ~/.ssh/known_hosts
}

#
install_necessary_packages() {
	HOSTNAMES=( $@ )
	
	PID_LIST=""
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		ssh root@${HOSTNAME} 'bash -s' >> /dev/null 2>&1 & <<'ENDSSH'
			apt-get update
			apt-get -y install ssh openssh-server screen expect bc build-essential nscd whois
ENDSSH
		PID_LIST=${PID_LIST}' '$!
	done
		
	wait_all ${PID_LIST}
}

# destroy node
destroy_node() {
	HOSTNAME=$1

	# remove ssh fingerprint
	PUBLIC_IP=$(getent hosts ${HOSTNAME} | awk '{print $1}')
	ssh-keygen -R ${PUBLIC_IP}
	ssh-keygen -R ${HOSTNAME}
	
	# remove from registry
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} remove host ${HOSTNAME}
	
	# destroy droplet
	${PYTHON} ${SBIN_DIR}/destroy.py -c ${CLIENT_ID} -k ${API_KEY} -n ${HOSTNAME}
}

# destroy cluster
rm_cluster() {
	CLUSTER_NAME=$1

	${PYTHON} ${SBIN_DIR}/registry.py remove cluster ${CLUSTER_NAME}
	RETVAL=$?
	[ "${RETVAL}" -eq 1 ] && exit 1
	
	CURRENT_HOSTS_PATH=$(mktemp)
	REGISTERED_HOSTS_PATH=$(mktemp)
	UPDATED_HOSTS_PATH=$(mktemp)

	# get /etc/hosts entries which are not in registry. note: can be abstracted.
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} generate public ${REGISTERED_HOSTS_PATH}
	cp /etc/hosts ${CURRENT_HOSTS_PATH}
	grep -F -x -v -f ${REGISTERED_HOSTS_PATH} ${CURRENT_HOSTS_PATH} > ${UPDATED_HOSTS_PATH}
	CURRENT_HOSTS_PATH=${UPDATED_HOSTS_PATH}
	
	# unregister and destroy
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list cluster ${CLUSTER_NAME})
	HOSTNAMES=( ${RESULT} )

	for HOSTNAME in ${HOSTNAMES[@]}
	do
		destroy_node ${HOSTNAME}
	done

	# update /etc/hosts. note: can be abstracted.
	REGISTERED_HOSTS_PATH=$(mktemp)
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} generate public ${REGISTERED_HOSTS_PATH}
	cat ${REGISTERED_HOSTS_PATH} >> ${CURRENT_HOSTS_PATH}
	sudo cp ${CURRENT_HOSTS_PATH} /etc/hosts

	sudo service nscd restart > /dev/null 2>&1
}

# configure hadoop slave node.
configure_hadoop_slave() {
	HOSTNAME=$1
	
	ssh root@${HOSTNAME} SNAPPY_VERSION=${SNAPPY_VERSION} USERNAME=${REMOTE_HOST_USER} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH'
	apt-get update

	# install java 7
	apt-get -y install software-properties-common python-software-properties
	add-apt-repository -y ppa:webupd8team/java
	apt-get update
	echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections
	echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections
	apt-get -y --force-yes install oracle-java7-installer oracle-java7-set-default

	# configure snappy
	wget https://snappy.googlecode.com/files/snappy-${SNAPPY_VERSION}.tar.gz
	tar -xvf snappy-${SNAPPY_VERSION}.tar.gz
	cd snappy-${SNAPPY_VERSION}
	./configure --enable-shared
	make && make install
	cd ..
	rm -rf snappy-${SNAPPY_VERSION}
	rm snappy-${SNAPPY_VERSION}.tar.gz

	# create user 'hduser'
	addgroup hadoop
	useradd -m -g hadoop -p $(mkpasswd ${USERNAME}) ${USERNAME}
	usermod -s /bin/bash ${USERNAME}
ENDSSH
	
	# add ssh fingerprint (user)
	${SBIN_DIR}/copy-ssh.ex ${HOME}/.ssh/id_rsa.pub ${HOSTNAME} ${REMOTE_HOST_USER} ${REMOTE_HOST_PASSWD} > /dev/null 2>&1
	
	ssh ${REMOTE_HOST_USER}@${HOSTNAME} HADOOP_VERSION=${HADOOP_VERSION} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH'
	# setup ssh
	ssh-keygen -t rsa -P "" -f ~/.ssh/id_rsa
	cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
	ssh-keyscan -H localhost >> ~/.ssh/known_hosts

	# mkdir

	mkdir -p ${HOME}/opt
	mkdir ${HOME}/var/hadoop/tmp
	mkdir ${HOME}/var/hdfs

	# install hadoop

	wget http://mirror.apache-kr.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}-bin.tar.gz
	tar -xvf hadoop-${HADOOP_VERSION}-bin.tar.gz
	mv hadoop-${HADOOP_VERSION} ~/opt/hadoop
	rm hadoop-${HADOOP_VERSION}-bin.tar.gz
	cp /usr/local/lib/libsnappy.so ~/opt/hadoop/lib/native/Linux-amd64-64/
ENDSSH
	
	# copy settings
	scp ${WORKING_DIR}/hadoop-env.sh ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/ # > /dev/null 2>&1
	scp ${WORKING_DIR}/core-site.xml ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/
	scp ${WORKING_DIR}/mapred-site.xml ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/
	scp ${WORKING_DIR}/hdfs-site.xml ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/
	scp ${WORKING_DIR}/masters ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/
	scp ${WORKING_DIR}/slaves ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/conf/
}

# generate hadoop settings
generate_hadoop_settings() {
	CLUSTER_NAME=$1
	MASTER_HOSTNAME=$2
	
	SMALLEST_SIZE=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list minsize ${CLUSTER_NAME})
	RESULT=$(${PYTHON} ${SBIN_DIR}/hadoop_conf.py ${SMALLEST_SIZE})
	TOKENS=( ${RESULT} )
	MAP_TASK_MAX=${TOKENS[0]}
	REDUCE_TASK_MAX=${TOKENS[1]}
	HEAP_MAX=${TOKENS[2]}
	TASK_HEAP_MAX=${TOKENS[3]}

	# create hadoop-env.sh
	sed "s/VAR_HEAP_MAX/${HEAP_MAX}/" ${TEMPLATE_DIR}/hadoop-env.sh > ${WORKING_DIR}/hadoop-env.sh

	# create core-site.xml
	sed "s/VAR_NAMENODE/${MASTER_HOSTNAME}/" ${TEMPLATE_DIR}/core-site.xml > ${WORKING_DIR}/core-site.xml

	# create mapred-site.xml
	sed "s/VAR_NAMENODE/${MASTER_HOSTNAME}/;s/VAR_MAP_TASK_MAX/${MAP_TASK_MAX}/;s/VAR_REDUCE_TASK_MAX/${REDUCE_TASK_MAX}/;s/VAR_TASK_HEAP_MAX/${TASK_HEAP_MAX}/;s/VAR_HEAP_MAX/${HEAP_MAX}/" ${TEMPLATE_DIR}/mapred-site.xml > ${WORKING_DIR}/mapred-site.xml

	# create hdfs-site.xml
	cp ${TEMPLATE_DIR}/hdfs-site.xml ${WORKING_DIR}/hdfs-site.xml

	# create masters
	echo "${MASTER_HOSTNAME}" > ${WORKING_DIR}/masters

	# create slaves
	touch ${WORKING_DIR}/slaves
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list cluster ${CLUSTER_NAME})
	HOSTNAMES=( ${RESULT} )
	
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		echo ${HOSTNAME} >> ${WORKING_DIR}/slaves
	done
}

configure_hadoop_slave_all() {
	CLUSTER_NAME=$1
	MASTER_HOSTNAME=$2
	
	generate_hadoop_settings ${CLUSTER_NAME} ${MASTER_HOSTNAME}
	
	# configure slaves
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list cluster ${CLUSTER_NAME})
	HOSTNAMES=( ${RESULT} )
	
	PID_LIST=""
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		configure_hadoop_slave ${HOSTNAME} &
		PID_LIST=${PID_LIST}' '$!
	done
	
	${PYTHON} - ${PID_LIST} << 'EOF'
#!/usr/bin/python3

import sys, psutil

def main():
	waitfor = set([ int(pid) for pid in sys.argv[1:] ])

	while waitfor:
		waitfor.intersection_update(set(psutil.get_pid_list()))

	return 0;

if __name__ == "__main__":
	sys.exit(main())
EOF

	rm ${WORKING_DIR}/hadoop-env.sh
	rm ${WORKING_DIR}/core-site.xml
	rm ${WORKING_DIR}/mapred-site.xml
	rm ${WORKING_DIR}/hdfs-site.xml
	rm ${WORKING_DIR}/masters
	rm ${WORKING_DIR}/slaves
}

# configure hadoop master node.
configure_hadoop_master() {
	CLUSTER_NAME=$1
	HOSTNAME=$2

	# install packages
	ssh root@${HOSTNAME} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH'
	apt-get update

	# configure python
	apt-get -y install python3 python3-dev python3-pip python3-numpy python3-scipy
	pip3 install reservoir-sampling-cli
ENDSSH

	# configure tools
	ssh -n ${REMOTE_HOST_USER}@${HOSTNAME} 'mkdir -p ~/bin'
	scp ${SBIN_DIR}/copy-ssh-first.ex ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ # > /dev/null 2>&1
	scp ${SBIN_DIR}/distconf ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ # > /dev/null 2>&1
	# scp ${SBIN_DIR}/mappercount ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ > /dev/null 2>&1
	# scp ${SBIN_DIR}/reducercount ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ > /dev/null 2>&1
	
	ssh ${REMOTE_HOST_USER}@${HOSTNAME} 'bash -s' <<ENDSSH
	echo '' >> ~/.bashrc
	echo "export HADOOP_INSTALL=~/opt/hadoop" >> ~/.bashrc
	echo 'export PATH=\${PATH}:~/bin:\${HADOOP_INSTALL}/bin' >> ~/.bashrc
ENDSSH

	# configure ssh key
	ssh ${REMOTE_HOST_USER}@${HOSTNAME} 'bash -s' <<ENDSSH
	while read SLAVE_HOSTNAME
	do
		\${HOME}/bin/copy-ssh-first.ex \${HOME}/.ssh/id_rsa.pub \${SLAVE_HOSTNAME} ${REMOTE_HOST_USER} ${REMOTE_HOST_PASSWD}
		ssh-keyscan -H \${SLAVE_HOSTNAME} >> \${HOME}/.ssh/known_hosts
	done < \${HOME}/opt/hadoop/conf/slaves
ENDSSH
}
