#!/usr/bin/python3

import os, sys, json

def load_registry(regFile):
	"""
		Read registry status from rfile. If it does not exist, creates it.
		
		Args:
		  @type regFile: File
		  @param regFile: Registry file
		  
		Returns:
		  @return: dict
	"""
	try:
		return json.load(regFile)
	except Exception as e:
		return { 'clusters': [], 'entries': [] }
	
def save_registry(regFile, regData):
	"""
		Write registry status to given file.
	"""
	regFile.write(json.dumps(regData, indent=2))

def add_host(regStatus, hostname, size):
	if any(e['hostname'] == hostname for e in regStatus['entries']):
		raise ValueError('host %s already exists' % hostname)
	else:
		# todo: entries -> hosts
		# todo: hostname -> name
		regStatus['entries'].append({ 'hostname': hostname, 'size': size })

def add_cluster(regStatus, clustername, role):
	if any(c['name'] == clustername for c in regStatus['clusters']):
		raise ValueError('cluster %s already exists' % clustername)
	else:
		if role in { 'hadoop' }:
			regStatus['clusters'].append({ 'name': clustername, 'role': role })
		else:
			raise ValueError('Invalid role: %s' % role)

def display_all_clusters_info(regStatus):	
	clusters = [ c['name'] for c in regStatus['clusters'] if 'cluster' in c ]
	
	print('Currently, %d clusters exist.' % len(clusters))
	print()
	
	for cluster in clusters:
		display_cluster_info(regStatus, cluster)
		print()
	
	display_unassigned_hosts(regStatus)

def display_cluster_info(regStatus, clustername):
	"""
		Show information of specified cluster.
	"""

	# find cluster
	cluster = next(( c['name'] for c in regStatus['clusters'] if 'name' in c and c['name'] == clustername), None)

	if cluster:	
		# all hosts in given cluster
		hosts = [ e['hostname'] for e in regStatus['entries'] if 'cluster' in e and e['cluster'] == clustername ]
		
		if 'role' in cluster:
			print('Cluster %s: %s cluster, %d nodes.' % (cluster['name'], cluster['role'], len(hosts)))
		else:
			print('Cluster %s: No role specified, %d nodes.' % (cluster['name'], len(hosts)))
		
		print('  ' + ', '.join(hosts))
	else:
		raise ValueError('Cluster %s does not exist' % clustername)

def display_unassigned_hosts(regStatus):
	# collect all unassigned nodes
	hosts = [ e['hostname'] for e in regStatus['entries'] if 'cluster' not in e or e['cluster'] == '' ]
	
	print('Unassigned: %d nodes.' % len(hosts))
	print('  ' + ', '.join(hosts))

def ip_address_assigned(host):
	p1 = host.get('public', '')
	p2 = host.get('private', '')

	if p1 and p2:
		return True
	else:
		return False

def write_public_hosts_entries(regStatus, hostsPath):
	"""
		Write public ip - hostname mapping of each formatted host, to given path.
	"""
	with open(hostsPath, "w+") as f:
		for host in (e for e in regStatus['entries']):
			if ip_address_assigned(host):
				f.write('{ip}\t{hostname}\n'.format(hostname = host['hostname'], ip = host['public']))

PRIVATE_HOSTS_TEMPLATE = '''127.0.0.1	localhost

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

'''

def write_private_hosts(regStatus, hostsPath, nname):
	"""
		Write hosts file for given namespace, to given path.
	"""
	with open(hostsPath, "w+") as f:
		f.write(PRIVATE_HOSTS_TEMPLATE)
		
		for host in (e for e in regStatus['entries'] if 'namespace' in e and e['namespace'] == nname):
			f.write('{ip}\t{hostname}\n'.format(hostname = host['hostname'], ip = host['private']))

def assign_ip_address(regStatus, hostname, public_ip, private_ip):
	"""
		Add public ip, private ip into given hostname. If host with given hostname does not exist
		in registry or it already has public ip or private ip, raise ValueError.
	"""
	host = next((e for e in regStatus['entries'] if e['hostname'] == hostname), None)
	
	if host:
		if not ip_address_assigned(host):
			host['public'] = public_ip
			host['private'] = private_ip
		else:
			raise ValueError('IP addresses already assigned: %s' % hostname)
	else:
		raise ValueError('host %s does not exist' % hostname)

def assign_to_namespace(regStatus, nsname, hostname):
	"""
		assign a namespace into host with given hostname
	"""
	host = next((e for e in regStatus['entries'] if e['hostname'] == hostname), None)

	if host:
		if ip_address_assigned(host):
			host['namespace'] = nsname
		else:
			raise ValueError('IP addresses not assigned yet: %s' % hostname)
	else:
		raise ValueError('host %s does not exist' % hostname)

def assign_to_cluster(regStatus, clustername, hostname):
	"""
		assign a namespace into host with given hostname 
	"""
	host = next((e for e in regStatus['entries'] if e['hostname'] == hostname), None)

	if host:
		if ip_address_assigned(host):
			host['cluster'] = clustername
		else:
			raise ValueError('IP addresses not assigned yet: %s' % hostname)
	else:
		raise ValueError('host %s does not exist' % hostname)
		
def list_cluster_hosts(regStatus, clustername):
	print('\t'.join([ e['hostname'] for e in regStatus['entries'] if 'cluster' in e and e['cluster'] == clustername ]))
		
def list_namespace_hosts(regStatus, nsname):
	print('\t'.join([ e['hostname'] for e in regStatus['entries'] if 'cluster' in e and e['namespace'] == nsname ]))

def minsize(regStatus, clustername):
	sizes = [ e['size'] for e in regStatus['entries'] if 'cluster' in e and e['cluster'] == clustername ]
	print(min(sizes))

def list_raw_hosts(regStatus):
	raw_hosts = [ e['hostname'] for e in regStatus['entries'] if not ip_address_assigned(e) ]
	print('\t'.join(raw_hosts))

def remove_host(regStatus, hostname):
	host = next((e for e in regStatus['entries'] if e['hostname'] == hostname), None)
	
	if host:
		regStatus['entries'].remove(host)
	else:
		raise ValueError('host %s does not exist' % hostname)

def remove_cluster(regStatus, clustername):
	cluster = next((c for c in regStatus['clusters'] if c['name'] == clustername), None)
	
	if cluster:
		regStatus['clusters'].remove(cluster)
	else:
		raise ValueError('cluster %s does not exist' % clustername)

# command procedures

def add_command(regStatus, argv):
	if argv:
		dst = argv[0]
		
		if 'host' == dst:
			if 3 == len(argv):
				hostname = argv[1]
				size = int(argv[2])
				add_host(regStatus, hostname, size)
			else:
				raise ValueError('Incorrect arguments for add host: %s' % ' '.join(argv[1:]))
		elif 'cluster' == dst:
			if 3 == len(argv):
				clustername = argv[1]
				role = argv[2]
				add_cluster(regStatus, clustername, role)
			else:
				raise ValueError('Incorrect arguments for add cluster: %s' % ' '.join(argv[1:]))
		else:
			raise ValueError('Incorrect arguments for add: %s' % ' '.join(argv))
			
		return 1
	else:
		raise ValueError('Incorrect arguments for add: %s' % ' '.join(argv))

def display_command(regStatus, argv):
	if 1 == len(argv):
		dst = argv[0]
		
		if '--all' == dst:
			display_all_clusters_info(regStatus)
		else:
			display_cluster_info(regStatus, dst)
		
		return 0
	else:
		raise ValueError('Incorrect arguments for ls: %s' % ' '.join(argv))

def generate_command(regStatus, argv):
	if argv:
		dst = argv[0]
	
		if 'public' == dst:
			if 2 == len(argv):
				hostsPath = argv[1]
				write_public_hosts_entries(regStatus, hostsPath)
			else:
				raise ValueError('Incorrect arguments for generate public: %s' % ' '.join(argv[1:]))
		elif 'private' == dst:
			if 3 == len(argv):
				hostsPath = argv[1]
				namespace = argv[2]
				write_private_hosts(regStatus, hostsPath, namespace)
			else:
				raise ValueError('Incorrect arguments for generate private: %s' % ' '.join(argv[1:]))
		else:
			raise ValueError('Incorrect arguments for generate: %s' % ' '.join(argv))
		
		return 0
	else:
		raise ValueError('Incorrect arguments for generate: %s' % ' '.join(argv))

def assign_command(regStatus, argv):
	if argv:
		dst = argv[0]
	
		if 'address' == dst:
			if 4 == len(argv):
				hostname = argv[1]
				public_ip = argv[2]
				private_ip = argv[3]
				assign_ip_address(regStatus, hostname, public_ip, private_ip)
			else:
				raise ValueError('Incorrect arguments for assign address: %s' % ' '.join(argv[1:]))
		elif 'cluster' == dst:
			if 3 == len(argv):
				clustername = argv[1]
				hostname = argv[2]
				assign_to_cluster(regStatus, clustername, hostname)
			else:
				raise ValueError('Incorrect arguments for assign cluster: %s' % ' '.join(argv[1:]))
		elif 'namespace' == dst:
			if 3 == len(argv):
				nsname = argv[1]
				hostname = argv[2]
				assign_to_namespace(regStatus, nsname, hostname)
			else:
				raise ValueError('Incorrect arguments for assign namespace: %s' % ' '.join(argv[1:]))
		else:
			raise ValueError('Incorrect arguments for assign: %s' % ' '.join(argv))
		
		return 1
	else:
		raise ValueError('Incorrect arguments for assign: %s' % ' '.join(argv))

def list_command(regStatus, argv):
	if argv:
		dst = argv[0]
	
		if 'cluster' == dst:
			if 2 == len(argv):
				clustername = argv[1]
				list_cluster_hosts(regStatus, clustername)
			else:
				raise ValueError('Incorrect arguments for list cluster: %s' % ' '.join(argv[1:]))
		elif 'namespace' == dst:
			if 2 == len(argv):
				nsname = argv[1]
				list_namespace_hosts(regStatus, nsname)
			else:
				raise ValueError('Incorrect arguments for list namespace: %s' % ' '.join(argv[1:]))
		elif 'minsize' == dst:
			if 2 == len(argv):
				clustername = argv[1]
				minsize(regStatus, clustername)
			else:
				raise ValueError('Incorrect arguments for list minsize: %s' % ' '.join(argv[1:]))
		elif 'raw' == dst:
			list_raw_hosts(regStatus)
		else:
			raise ValueError('Incorrect arguments for list: %s' % ' '.join(argv))
		
		return 0
	else:
		raise ValueError('Incorrect arguments for list: %s' % ' '.join(argv))

def remove_command(regStatus, argv):
	if argv:
		dst = argv[0]
	
		if 'host' == dst:
			if 2 == len(argv):
				hostname = argv[1]
				remove_host(regStatus, hostname)
			else:
				raise ValueError('Incorrect arguments for remove host: %s' % ' '.join(argv[1:]))
		elif 'cluster' == dst:
			if 2 == len(argv):
				clustername = argv[1]
				remove_cluster(regStatus, clustername)
			else:
				raise ValueError('Incorrect arguments for remove cluster: %s' % ' '.join(argv[1:]))
		else:
			raise ValueError('Incorrect arguments for remove: %s' % ' '.join(argv))
		
		return 1
	else:
		raise ValueError('Incorrect arguments for remove: %s' % ' '.join(argv))

def main():
	regPath = sys.argv[1]
	command = sys.argv[2]
	
	procedures = {
		'add': add_command,
		'display': display_command,
		'generate': generate_command,
		'assign': assign_command,
		'list': list_command,
		'remove': remove_command,
	}
	
	try:
		# read current registry status
		with open(regPath, "r+") as regFile:
			regStatus = load_registry(regFile)
		
		# conduct command
		if command in procedures:
			procedure = procedures[command]
			updated = procedure(regStatus, sys.argv[3:])

			# write current registry status, if required
			if updated:
				os.remove(regPath)
				with open(regPath, "w") as regFile:
					save_registry(regFile, regStatus)
		else:
			raise ValueError('Unknown command: %s' % command)

	except Exception as e:
		print(e)
		return 1

	return 0

if __name__ == '__main__':
	sys.exit(main())
