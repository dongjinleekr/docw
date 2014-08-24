#!/usr/bin/python3
'''
Created on Mar 26, 2014

@author: dongjinleekr
'''

import sys, argparse
from dopy.manager import DoManager

def main():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('-c', '--client-id', type=str, required=True, help='')
	parser.add_argument('-a', '--api-key', type=str, required=True, help='')
	parser.add_argument('-n', '--hostname', type=str, required=True, help='')

	parsed = parser.parse_args(sys.argv[1:])
	args = vars(parsed)

	hostname = args['hostname']

	try:
		do = DoManager(args['client_id'], args['api_key'])
		droplet = next((item for item in do.all_active_droplets() if item['name'] == hostname))
		
		print("%s\t%s" % (droplet['ip_address'], droplet['private_ip_address']))
		
		return 0
					
	except Exception as e:
		print(e)
		return 1

	return 0

if __name__ == '__main__':
	sys.exit(main())
