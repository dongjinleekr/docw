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

def add_host_entry(data, clustername, hostname, public_ip, private_ip):
	if any(entry['hostname'] == hostname for entry in data['entries']):
		raise ValueError('Duplicated hostname')
	else:
		ret = copy.deepcopy(data)
		ret['entries'].append({ 'hostname': hostname, 'clustername': clustername, 'public': public_ip, 'private': private_ip })
		return ret

def remove_host_entry(data, hostname):
	ret = copy.deepcopy(data)
	e = next((entry for entry in ret['entries'] if entry['hostname'] == hostname), None)
	
	if e:
		ret['entries'].remove(e)
		return ret
	else:
		raise ValueError('Duplicated hostname')

def add_public_hosts(f, data):
	for entry in ('%s\t%s\n' % (entry['public'], entry['hostname']) for entry in data['entries']):
		f.write(entry)

def remove_public_hosts(f, g, data):
	entries = ['%s\t%s' % (entry['public'], entry['hostname']) for entry in data['entries']]

	for line in f:
		if line.strip() not in entries:
			g.write(line)

PRIVATE_HOSTS_TEMPLATE = '''127.0.0.1	localhost

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

'''

def generate_private_hosts(f, data):
	f.write(PRIVATE_HOSTS_TEMPLATE)
	for entry in data['entries']:
		f.write('{ip}\t{hostname}\n'.format(hostname = entry['hostname'], ip = entry['private']))

def add_host(registry, public_hosts, private_hosts, clustername, hostname, public_ip, private_ip):

	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
			
		# clean hosts
		with open(public_hosts, "r") as f:
			updated_hosts_fd, updated_hosts_path = tempfile.mkstemp()
			with closing(os.fdopen(updated_hosts_fd, 'w')) as g:
				remove_public_hosts(f, g, data)
	
		# add registry
		data = add_host_entry(data, clustername, hostname, public_ip, private_ip)
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)
		
		# add public hosts
		with open(updated_hosts_path, 'a') as f:
			add_public_hosts(f, data)
		
		shutil.copy(updated_hosts_path, public_hosts)
			
		with open(private_hosts, "w+") as f:
			generate_private_hosts(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def remove_host(registry, public_hosts, private_hosts, hostname):

	try:
		# read registry
		with open(registry, "r+") as f:
			data = load_registry(f)
			
		# clean hosts
		with open(public_hosts, "r") as f:
			updated_hosts_fd, updated_hosts_path = tempfile.mkstemp()
			with closing(os.fdopen(updated_hosts_fd, 'w')) as g:
				remove_public_hosts(f, g, data)
		
		# remove registry
		data = remove_host_entry(data, hostname)
		
		os.remove(registry)
		with open(registry, "w") as f:
			save_registry(f, data)
		
		# add public hosts
		with open(updated_hosts_path, 'a') as f:
			add_public_hosts(f, data)
		
		shutil.copy(updated_hosts_path, public_hosts)
			
		with open(private_hosts, "w+") as f:
			generate_private_hosts(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0
		
def list_hosts(registry, clustername):
	with open(registry, "r+") as f:
		data = load_registry(f)
		print('\t'.join([ entry['hostname'] for entry in data['entries'] if entry['clustername'] == clustername ]))

def minsize(registry, clustername):
	with open(registry, "r+") as f:
		data = load_registry(f)
		sizes = [ int(entry['size']) for entry in data['entries'] \
							if entry['clustername'] == clustername ]
		print(min(sizes))

def main():
	registry = sys.argv[1]
	
	if 'add' == sys.argv[2] and 9 == len(sys.argv):
		public_hosts = sys.argv[3]
		private_hosts = sys.argv[4]
		clustername = sys.argv[5]
		hostname = sys.argv[6]
		public_ip = sys.argv[7]
		private_ip = sys.argv[8]
		add_host(registry, public_hosts, private_hosts, clustername, hostname, public_ip, private_ip)
	elif 'remove' == sys.argv[2] and 6 == len(sys.argv):
		public_hosts = sys.argv[3]
		private_hosts = sys.argv[4]
		hostname = sys.argv[5]
		remove_host(registry, public_hosts, private_hosts, hostname)
	elif 'list' == sys.argv[2] and 4 == len(sys.argv):
		clustername = sys.argv[3]
		list_hosts(registry, clustername)
	elif 'minsize' == sys.argv[2] and 4 == len(sys.argv):
		clustername = sys.argv[3]
		minsize(registry, clustername)
	else:
		print('error')
		
	return 0

if __name__ == '__main__':
	sys.exit(main())
