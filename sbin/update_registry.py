#!/usr/bin/python3

import os, sys, argparse, json
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

def add_host_entry(data, hostname, public_ip, private_ip):
	if any(entry['hostname'] == hostname for entry in data['entries']):
		raise ValueError('Duplicated hostname')
	else:
		ret = copy.deepcopy(data)
		ret['entries'].append({ 'hostname': hostname, 'public': public_ip, 'private': private_ip })
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
127.0.1.1	VAR_HOSTNAME

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

def add_host(**args):

	try:
		# read registry
		with open(args['registry'], "r+") as f:
			data = load_registry(f)
			
		# clean hosts
		with open(args['public_hosts'], "r") as f:
			updated_hosts_fd, updated_hosts_path = tempfile.mkstemp()
			with closing(os.fdopen(updated_hosts_fd, 'w')) as g:
				remove_public_hosts(f, g, data)
	
		# add registry
		data = add_host_entry(data, args['hostname'], args['public_ip'], args['private_ip'])
		
		os.remove(args['registry'])
		with open(args['registry'], "w") as f:
			save_registry(f, data)
		
		# add public hosts
		with open(updated_hosts_path, 'a') as f:
			add_public_hosts(f, data)
		
		shutil.copy(updated_hosts_path, args['public_hosts'])
			
		with open(args['private_hosts'], "w+") as f:
			generate_private_hosts(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def remove_host(**args):

	try:
		# read registry
		with open(args['registry'], "r+") as f:
			data = load_registry(f)
			
		# clean hosts
		with open(args['public_hosts'], "r") as f:
			updated_hosts_fd, updated_hosts_path = tempfile.mkstemp()
			with closing(os.fdopen(updated_hosts_fd, 'w')) as g:
				remove_public_hosts(f, g, data)
		
		# remove registry
		data = remove_host_entry(data, args['hostname'])
		
		os.remove(args['registry'])
		with open(args['registry'], "w") as f:
			save_registry(f, data)
		
		# add public hosts
		with open(updated_hosts_path, 'a') as f:
			add_public_hosts(f, data)
		
		shutil.copy(updated_hosts_path, args['public_hosts'])
			
		with open(args['private_hosts'], "w+") as f:
			generate_private_hosts(f, data)

	except Exception as e:
		print(e)
		return 1

	return 0

def main():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('-r', '--registry', type=str, required=True, help='')
	parser.add_argument('-s', '--public-hosts', type=str, required=True, help='')
	parser.add_argument('-t', '--private-hosts', type=str, required=True, help='')
	parser.add_argument('-n', '--hostname', type=str, required=True, help='')
	parser.add_argument('-u', '--public-ip', type=str, required=False, help='')
	parser.add_argument('-v', '--private-ip', type=str, required=False, help='')

	# http://mkaz.com/2014/07/26/python-argparse-cookbook/
	parsed = parser.parse_args(sys.argv[2:])
	args = vars(parsed)
	
	if 'add' == sys.argv[1]:
		add_host(**args)
	elif 'remove' == sys.argv[1]:
		remove_host(**args)
	else:
		print('error')

if __name__ == '__main__':
	sys.exit(main())
