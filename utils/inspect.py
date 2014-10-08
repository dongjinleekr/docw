#!/usr/bin/python3
'''
Created on Mar 26, 2014

@author: dongjinleekr
'''

import sys
from dopy.manager import DoManager

def printHelp():
	helpMsg = '''usage: retrieve_droplet_ip.py ([-h]) [client id] [api key] [hostname]

Retrieve public/private ip address of digitalocean droplet, whose client id, api key and hostname are given.

positional arguments:
  client id\tuser's digitalocean(tm) client id
  api key\tuser's digitalocean(tm) api key
  hostname\thostname of desired droplet
	'''
	print(helpMsg)

def process(client_id, api_key, hostname):
	try:
		do = DoManager(client_id, api_key)
		droplet = next((item for item in do.all_active_droplets() if item['name'] == hostname), None)
		
		if droplet:
			print("%s\t%s" % (droplet['ip_address'], droplet['private_ip_address']))
			return 0
		else:
			raise ValueError('No droplet exists named %s' % hostname)
					
	except Exception as e:
		print(e)
		return 1

def main():
	if 2 == len(sys.argv) and '-h' == sys.argv[1]:
		printHelp()
		return 0
	elif 4 == len(sys.argv):
		return process(sys.argv[1], sys.argv[2], sys.argv[3])
	else:
		print('Bad arguments: %s' ' '.join(sys.argv[1:]))
		printHelp()
		return 1

if __name__ == '__main__':
	sys.exit(main())
