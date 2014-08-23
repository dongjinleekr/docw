#!/usr/bin/python3

import os, sys, argparse, json
import shutil
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

def add_host_entry(f, hostname, public_ip, private_ip):
	data = load_registry(f)
	entries = data['entries']
	
	if any(e['hostname'] == hostname for e in entries):
		raise ValueError('Duplicated hostname')
	else:
		entries.append({ 'hostname': hostname, 'public': public_ip, 'private': private_ip })
		save_registry(f, data)
		return data

def generate_public_hosts(f, g, entries):
	entry_list = [ '%s\t%s' % (entry['public'], entry['hostname']) for entry in entries ]

	for line in f:
		if not line.strip() in entry_list:
			g.write(line)

	for entry in entry_list:
		g.write(entry + '\n')

PRIVATE_HOSTS_TEMPLATE = '''127.0.0.1	localhost
127.0.1.1	VAR_HOSTNAME

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

'''

def generate_private_hosts(f, entries):
	f.write(PRIVATE_HOSTS_TEMPLATE)
	for entry in entries:
		f.write('{ip}\t{hostname}\n'.format(hostname = entry['hostname'], ip = entry['private']))

def add_host(**args):

	try:
		with open(args['registry'], "r+") as f:
			data = add_host_entry(f, args['hostname'], args['public_ip'], args['private_ip'])
			
		with open(args['public_hosts'], "r") as f:
			updated_hosts_fd, updated_hosts_path = tempfile.mkstemp()
			with closing(os.fdopen(updated_hosts_fd, 'w')) as g:
				generate_public_hosts(f, g, data['entries'])
		
		shutil.copy(updated_hosts_path, args['public_hosts'])
			
		with open(args['private_hosts'], "w+") as f:
			generate_private_hosts(f, data['entries'])

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
		print('remove')
	else:
		print('error')

if __name__ == '__main__':
	sys.exit(main())
