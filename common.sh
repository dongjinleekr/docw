# exe
PYTHON=$(which python3)

# executables
BASE_DIR=$(dirname $(dirname $(readlink -f $0)))
SBIN_DIR=${BASE_DIR}/sbin
TOOLS_DIR=${BASE_DIR}/tools
TEMPLATE_DIR=${BASE_DIR}/templates

# settings
SETTINGS_DIR=${HOME}/.docw
REGISTRY_PATH=${SETTINGS_DIR}/registry
ID_SEQUENCE_PATH=${SETTINGS_DIR}/sequence
CFG_PATH=${SETTINGS_DIR}/config.cfg

[ -d "${SETTINGS_DIR}" ] || mkdir ${SETTINGS_DIR}
[ -f "${REGISTRY_PATH}" ] || echo '{ "entries": [], "clusters": [] }' > ${REGISTRY_PATH}
[ -f "${ID_SEQUENCE_PATH}" ] || echo '0' > ${ID_SEQUENCE_PATH}
[ -f "${CFG_PATH}" ] || { cp ${BASE_DIR}/config-template.cfg ${CFG_PATH}; echo "config missing: please edit ${CFG_PATH}"; exit 0;}

. ${CFG_PATH}

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

# validation procedures

validate_mkcluster() {
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} validate mkcluster ${@}
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
		scp ${HOSTS_PATH} root@${HOSTNAME}:/etc/hosts > /dev/null 2>&1
		ssh -n root@${HOSTNAME} 'service nscd restart' > /dev/null 2>&1
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
	TMP_PASSWORD=$(${PYTHON} ${SBIN_DIR}/fetchmail.py ${CLIENT_ID} ${API_KEY} ${EMAIL_SERVER} ${EMAIL_USERNAME} ${EMAIL_PASSWORD} ${HOSTNAME})
	[ -z "${TMP_PASSWORD}" ] && return 1

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

	${TOOLS_DIR}/mkmaster root ${ROOT_PASSWORD} ${HOSTNAME} > /dev/null 2>&1

	ssh-keyscan -H ${PUBLIC_IP} >> ~/.ssh/known_hosts
	ssh-keyscan -H ${HOSTNAME} >> ~/.ssh/known_hosts
}

raw_hosts() {
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list raw
}

format_hosts() {
	# todo: input validation
	PID_LIST=""
	
	for HOSTNAME in $@
	do
		assign_ip_address ${HOSTNAME}
		
		# 1. install essential packages & create user
		ssh root@${HOSTNAME} USERNAME=${REMOTE_HOST_USER} TIMEZONE=${TIMEZONE} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH' &
	apt-get update
	apt-get -y install ssh openssh-server screen expect bc build-essential nscd whois
	
	addgroup hadoop
	useradd -m -g hadoop -p $(mkpasswd ${USERNAME}) ${USERNAME}
	usermod -s /bin/bash ${USERNAME}
	
	ln -sf /usr/share/zoneinfo/${TIMEZONE} /etc/localtime
ENDSSH
		PID_LIST=${PID_LIST}' '$!
	done
	
	echo "Waiting for package installations to be completed..."
	wait_all ${PID_LIST}
	
	# 2. copy essential tools
	for HOSTNAME in $@
	do
		${TOOLS_DIR}/mkmaster --known ${REMOTE_HOST_USER} ${REMOTE_HOST_PASSWD} ${HOSTNAME} > /dev/null 2>&1
		
		ssh -n ${REMOTE_HOST_USER}@${HOSTNAME} 'mkdir -p ~/bin'
		scp ${TOOLS_DIR}/mkmaster ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ > /dev/null 2>&1
	done
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

	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} remove cluster ${CLUSTER_NAME}
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
	TEMP_HADOOP_ENV_PATH=$2
	TEMP_YARN_ENV_PATH=$3
	TEMP_CORE_SITE_PATH=$4
	TEMP_MAPRED_SITE_PATH=$5
	TEMP_HDFS_SITE_PATH=$6
	TEMP_YARN_SITE_PATH=$7
	TEMP_MASTERS_PATH=$8
	TEMP_SLAVES_PATH=$9
	
	# 1. install packages
	ssh root@${HOSTNAME} SNAPPY_VERSION=${SNAPPY_VERSION} USERNAME=${REMOTE_HOST_USER} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH'
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
ENDSSH
	
	# 2. install hadoop
	ssh ${REMOTE_HOST_USER}@${HOSTNAME} HADOOP_VERSION=${HADOOP_VERSION} 'bash -s' >> /dev/null 2>&1 <<'ENDSSH'
	# setup ssh
	ssh-keygen -t rsa -P "" -f ~/.ssh/id_rsa
	cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
	ssh-keyscan -H localhost >> ~/.ssh/known_hosts

	# mkdir

	mkdir -p ${HOME}/opt
	mkdir -p ${HOME}/var/hadoop/tmp
	mkdir -p ${HOME}/var/hdfs

	# install hadoop

	wget http://mirror.apache-kr.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz
	tar -xvf hadoop-${HADOOP_VERSION}.tar.gz
	mv hadoop-${HADOOP_VERSION} ~/opt/hadoop
	rm hadoop-${HADOOP_VERSION}.tar.gz
	cp /usr/local/lib/libsnappy.so ~/opt/hadoop/lib/native/
	
	echo '' >> ~/.bashrc
	echo "export HADOOP_PREFIX=~/opt/hadoop" >> ~/.bashrc
	echo 'export PATH=${PATH}:~/bin:${HADOOP_PREFIX}/bin:${HADOOP_PREFIX}/sbin' >> ~/.bashrc
ENDSSH
	
	# 3. copy settings
	scp ${TEMP_HADOOP_ENV_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/hadoop-env.sh # > /dev/null 2>&1
	scp ${TEMP_YARN_ENV_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/yarn-env.sh # > /dev/null 2>&1
	scp ${TEMP_CORE_SITE_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/core-site.xml # > /dev/null 2>&1
	scp ${TEMP_MAPRED_SITE_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/mapred-site.xml # > /dev/null 2>&1
	scp ${TEMP_HDFS_SITE_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/hdfs-site.xml # > /dev/null 2>&1
	scp ${TEMP_YARN_SITE_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/yarn-site.xml # > /dev/null 2>&1
	scp ${TEMP_MASTERS_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/masters # > /dev/null 2>&1
	scp ${TEMP_SLAVES_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/slaves # > /dev/null 2>&1

	# 4. copy tools
	scp ${TOOLS_DIR}/distconf ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ # > /dev/null 2>&1
	scp ${TOOLS_DIR}/boot-all ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ # > /dev/null 2>&1
	scp ${TOOLS_DIR}/unboot-all ${REMOTE_HOST_USER}@${HOSTNAME}:~/bin/ # > /dev/null 2>&1
}

# generate hadoop settings
generate_hadoop_settings() {
	CLUSTER_NAME=$1
	MASTER_HOSTNAME=$2
	TEMP_HADOOP_ENV_PATH=$3
	TEMP_YARN_ENV_PATH=$4
	TEMP_CORE_SITE_PATH=$5
	TEMP_MAPRED_SITE_PATH=$6
	TEMP_HDFS_SITE_PATH=$7
	TEMP_YARN_SITE_PATH=$8
	TEMP_MASTERS_PATH=$9
	TEMP_SLAVES_PATH=${10}
	
	SMALLEST_SIZE=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list minsize ${CLUSTER_NAME})
	HOST_COUNT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list size ${CLUSTER_NAME})
	
	RESULT=$(${PYTHON} ${SBIN_DIR}/hadoop_conf.py ${SMALLEST_SIZE} ${HOST_COUNT})
	TOKENS=( ${RESULT} )
	CONTAINER_HEAP_MAX=${TOKENS[0]}
	MAP_TASK_HEAP_MAX=${TOKENS[1]}
	REDUCE_TASK_HEAP_MAX=${TOKENS[2]}
	MAP_JVM_HEAP_MAX=${TOKENS[3]}
	REDUCE_JVM_HEAP_MAX=${TOKENS[4]}
	MAP_TASK_PER_NODE=${TOKENS[5]}
	REDUCE_TASK_PER_NODE=${TOKENS[6]}
	MAP_TASK_TOTAL=${TOKENS[7]}
	REDUCE_TASK_TOTAL=${TOKENS[8]}

	# create hadoop-env.sh
	sed "s/VAR_CONTAINER_HEAP_MAX/${CONTAINER_HEAP_MAX}/" ${TEMPLATE_DIR}/hadoop/hadoop-env.sh > ${TEMP_HADOOP_ENV_PATH}
	
	# create yarn-env.sh
	cp ${TEMPLATE_DIR}/hadoop/yarn-env.sh ${TEMP_YARN_ENV_PATH}

	# create core-site.xml
	sed "s/VAR_MASTER/${MASTER_HOSTNAME}/" ${TEMPLATE_DIR}/hadoop/core-site.xml > ${TEMP_CORE_SITE_PATH}

	# create mapred-site.xml
	sed "s/VAR_MASTER/${MASTER_HOSTNAME}/;s/VAR_MAP_TASK_HEAP_MAX/${MAP_TASK_HEAP_MAX}/;s/VAR_REDUCE_TASK_HEAP_MAX/${REDUCE_TASK_HEAP_MAX}/;s/VAR_MAP_JVM_HEAP_MAX/${MAP_JVM_HEAP_MAX}/;s/VAR_REDUCE_JVM_HEAP_MAX/${REDUCE_JVM_HEAP_MAX}/;s/VAR_MAP_TASK_PER_NODE/${MAP_TASK_PER_NODE}/;s/VAR_REDUCE_TASK_PER_NODE/${REDUCE_TASK_PER_NODE}/;s/VAR_MAP_TASK_TOTAL/${MAP_TASK_TOTAL}/;s/VAR_REDUCE_TASK_TOTAL/${REDUCE_TASK_TOTAL}/" ${TEMPLATE_DIR}/hadoop/mapred-site.xml > ${TEMP_MAPRED_SITE_PATH}

	# create hdfs-site.xml
	sed "s/VAR_MASTER/${MASTER_HOSTNAME}/" ${TEMPLATE_DIR}/hadoop/hdfs-site.xml > ${TEMP_HDFS_SITE_PATH}

	# create yarn-site.xml
	sed "s/VAR_MASTER/${MASTER_HOSTNAME}/;s/VAR_CONTAINER_HEAP_MAX/${CONTAINER_HEAP_MAX}/" ${TEMPLATE_DIR}/hadoop/yarn-site.xml > ${TEMP_YARN_SITE_PATH}

	# create masters
	echo "${MASTER_HOSTNAME}" > ${TEMP_MASTERS_PATH}

	# create slaves
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list cluster ${CLUSTER_NAME})
	HOSTNAMES=( ${RESULT} )
	
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		echo ${HOSTNAME} >> ${TEMP_SLAVES_PATH}
	done
}

configure_hadoop_slave_all() {
	CLUSTER_NAME=$1
	MASTER_HOSTNAME=$2
	
	TEMP_HADOOP_ENV_PATH=$(mktemp)
	TEMP_YARN_ENV_PATH=$(mktemp)
	TEMP_CORE_SITE_PATH=$(mktemp)
	TEMP_MAPRED_SITE_PATH=$(mktemp)
	TEMP_HDFS_SITE_PATH=$(mktemp)
	TEMP_YARN_SITE_PATH=$(mktemp)
	TEMP_MASTERS_PATH=$(mktemp)
	TEMP_SLAVES_PATH=$(mktemp)
	
	generate_hadoop_settings ${CLUSTER_NAME} ${MASTER_HOSTNAME} ${TEMP_HADOOP_ENV_PATH} ${TEMP_YARN_ENV_PATH} ${TEMP_CORE_SITE_PATH} ${TEMP_MAPRED_SITE_PATH} ${TEMP_HDFS_SITE_PATH} ${TEMP_YARN_SITE_PATH} ${TEMP_MASTERS_PATH} ${TEMP_SLAVES_PATH}
	
	# configure slaves
	RESULT=$(${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} list cluster ${CLUSTER_NAME})
	HOSTNAMES=( ${RESULT} )
	
	PID_LIST=""
	for HOSTNAME in ${HOSTNAMES[@]}
	do
		configure_hadoop_slave ${HOSTNAME} ${TEMP_HADOOP_ENV_PATH} ${TEMP_YARN_ENV_PATH} ${TEMP_CORE_SITE_PATH} ${TEMP_MAPRED_SITE_PATH} ${TEMP_HDFS_SITE_PATH} ${TEMP_YARN_SITE_PATH} ${TEMP_MASTERS_PATH} ${TEMP_SLAVES_PATH} &
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
}

# configure loginless connection between master host and all hosts in same cluster.
configure_master_host() {
	CLUSTER_NAME=$1
	MASTER_HOSTNAME=$2
	
	# 
	${PYTHON} ${SBIN_DIR}/registry.py ${REGISTRY_PATH} assign master ${CLUSTER_NAME} ${MASTER_HOSTNAME}

	ssh ${REMOTE_HOST_USER}@${MASTER_HOSTNAME} "/home/${REMOTE_HOST_USER}/bin/mkmaster ${REMOTE_HOST_USER} ${REMOTE_HOST_PASSWD} ${@:2}"
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
	
	# update yarn-site.xml
	TEMP_YARN_SITE_PATH=$(mktemp)
	scp ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/yarn-site.xml ${TEMP_YARN_SITE_PATH} # > /dev/null 2>&1
	
	sed -i "s/<\/configuration>/<property>\n<name>yarn.nodemanager.localizer.address<\/name>\n<value>${HOSTNAME}:8060<\/value>\n<\/property>\n<\/configuration>/" ${TEMP_YARN_SITE_PATH}
	
	scp ${TEMP_YARN_SITE_PATH} ${REMOTE_HOST_USER}@${HOSTNAME}:~/opt/hadoop/etc/hadoop/yarn-site.xml # > /dev/null 2>&1

	ssh -n ${REMOTE_HOST_USER}@${HOSTNAME} "/home/${REMOTE_HOST_USER}/opt/hadoop/bin/hadoop namenode -format" > /dev/null 2>&1
}
