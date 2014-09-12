#!/usr/bin/python3

import os, sys, json
import shutil
import copy
import tempfile

from contextlib import closing

def load_registry(f):
	try:
		return json.load(f)
	except Exception as e:
		return { 'entries': [] }
	
def save_registry(f, registry):
	f.seek(0)
	f.write(json.dumps(registry, indent=2))

def add_host_entry(data, hostname, size):
	if any(entry['hostname'] == hostname for entry in data['entries']):
		raise ValueError('Duplicated hostname')
	else:
		ret = copy.deepcopy(data)
		ret['entries'].append({ 'hostname': hostname, 'size': size })
		return ret

def is_formatted(host):
	if 'public' in host and 'private' in host:
		return True
	else:
		return False

def format_host_entry(data, hostname, public_ip, private_ip):
	"""
		add public ip, private ip into given hostname. If host with given hostname does not exist
		in registry or it already has public ip and private ip(already formatted), raise ValueError.
	"""
	host = next((entry for entry in data['entries'] if entry['hostname'] == hostname), None)
	
	if host:
		if not is_formatted(host):
			host['public'] = public_ip
			host['private'] = private_ip

			return data
		else:
			raise ValueError('already formatted')
	else:
		raise ValueError('host does not exist')

def remove_host_entry(data, hostname):
	ret = copy.deepcopy(data)
	e = next((entry for entry in ret['entries'] if entry['hostname'] == hostname), None)
	
	if e:
		ret['entries'].remove(e)
		return ret
	else:
		raise ValueError('Duplicated hostname')

PRIVATE_HOSTS_TEMPLATE = '''127.0.0.1	localhost

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

'''

def generate_private_hosts(registry, hosts, namespace):
	"""
		generate hosts file for given namespace
		
		Returns:
			path to generated file
	"""
	# read registry
	with open(registry, "r+") as f:
		data = load_registry(f)
	
	with open(hosts, "w+") as g:
		g.write(PRIVATE_HOSTS_TEMPLATE)
		
		for entry in (entry for entry in data['entries'] if 'namespace' in entry and entry['namespace'] == namespace):
			g.write('{ip}\t{hostname}\n'.format(hostname = entry['hostname'], ip = entry['private']))

def add_host(registry, hostname, size):

	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
	
		# add host
		data = add_host_entry(data, hostname, size)
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def format_host(registry, hostname, public_ip, private_ip):

	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
	
		# format host
		data = format_host_entry(data, hostname, public_ip, private_ip)
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def dump_hosts(registry, hosts):
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
		
		with open(hosts, "w+") as g:
			for entry in (entry for entry in data['entries']):
				if is_formatted(entry):
					g.write('{ip}\t{hostname}\n'.format(hostname = entry['hostname'], ip = entry['public']))

def add_to_namespace(registry, hostname, namespace):
	"""
		assign a namespace into host with given hostname
	"""
	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
			
		host = next((entry for entry in data['entries'] if entry['hostname'] == hostname), None)
	
		if host:
			if is_formatted(host):
				host['namespace'] = namespace
			else:
				raise ValueError('not formatted')
		else:
			raise ValueError('host does not exist')
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def add_to_cluster(registry, hostname, cluster):
	"""
		assign a namespace into host with given hostname 
	"""
	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
			
		host = next((entry for entry in data['entries'] if entry['hostname'] == hostname), None)
	
		if host:
			if is_formatted(host):
				host['cluster'] = cluster
			else:
				raise ValueError('not formatted')
		else:
			raise ValueError('host does not exist')
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def remove_host(registry, hostname):

	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
		
		# remove registry
		data = remove_host_entry(data, hostname)
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0
		
def list_hosts(registry, cluster):
	with open(registry, "r+") as f:
		data = load_registry(f)
		print('\t'.join([ entry['hostname'] for entry in data['entries'] if 'cluster' in entry and entry['cluster'] == cluster ]))
		
def list_namespace_hosts(registry, namespace):
	with open(registry, "r+") as f:
		data = load_registry(f)
		print('\t'.join([ entry['hostname'] for entry in data['entries'] if 'cluster' in entry and entry['namespace'] == namespace ]))

def minsize(registry, cluster):
	with open(registry, "r+") as f:
		data = load_registry(f)
		
	sizes = [ entry['size'] for entry in data['entries'] \
						if 'cluster' in entry and entry['cluster'] == cluster ]
	print(min(sizes))

def main():
	registry = sys.argv[1]
	
	if 'add' == sys.argv[2] and 5 == len(sys.argv):
		hostname = sys.argv[3]
		size = int(sys.argv[4])
		add_host(registry, hostname, size)
	elif 'format' == sys.argv[2] and 6 == len(sys.argv):
		hostname = sys.argv[3]
		public_ip = sys.argv[4]
		private_ip = sys.argv[5]
		format_host(registry, hostname, public_ip, private_ip)
	elif 'hosts' == sys.argv[2] and 4 == len(sys.argv):	# list all hosts
		hosts = sys.argv[3]
		dump_hosts(registry, hosts)
	elif 'private' == sys.argv[2] and 5 == len(sys.argv):
		hosts = sys.argv[3]
		namespace = sys.argv[4]
		generate_private_hosts(registry, hosts, namespace)
	elif 'namespace' == sys.argv[2] and 5 == len(sys.argv):
		namespace = sys.argv[3]
		hostname = sys.argv[4]
		add_to_namespace(registry, hostname, namespace)
	elif 'cluster' == sys.argv[2] and 5 == len(sys.argv):
		cluster = sys.argv[3]
		hostname = sys.argv[4]
		add_to_cluster(registry, hostname, cluster)
	elif 'remove' == sys.argv[2] and 4 == len(sys.argv):
		hostname = sys.argv[3]
		remove_host(registry, hostname)
	elif 'nslist' == sys.argv[2] and 4 == len(sys.argv):
		namespace = sys.argv[3]
		list_namespace_hosts(registry, namespace)
	elif 'list' == sys.argv[2] and 4 == len(sys.argv):
		cluster = sys.argv[3]
		list_hosts(registry, cluster)
	elif 'minsize' == sys.argv[2] and 4 == len(sys.argv):
		cluster = sys.argv[3]
		minsize(registry, cluster)
	else:
		print('error')
		
	return 0

if __name__ == '__main__':
	sys.exit(main())
