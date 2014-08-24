#!/usr/bin/python3
'''
Created on Mar 26, 2014

@author: dongjinleekr
'''

# example:
# python3 create.py -c njxEdecoXRqufrmc9xcJ9 -a d2cb3cd48a93da819e67c0eb8ad34196 -n testhost -s 62 -i ubuntu-14.04 -r sgp1

import sys, argparse
from dopy.manager import DoManager

IMAGE_ID_MAP = { 'ubuntu-14.04': 5141286 }
REGION_ID_MAP = { 'nyc2': 4, 'sgp1': 6 }

def main():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('-c', '--client-id', type=str, required=True, help='')
	parser.add_argument('-a', '--api-key', type=str, required=True, help='')
	parser.add_argument('-n', '--hostname', type=str, required=True, help='')
	parser.add_argument('-s', '--node-size', type=int, required=True, help='')
	parser.add_argument('-i', '--image', type=str, required=True, help='')
	parser.add_argument('-r', '--region', type=str, required=True, help='')

	parsed = parser.parse_args(sys.argv[1:])
	args = vars(parsed)

	hostname = args['hostname']
	size = args['node_size']
	image_id = IMAGE_ID_MAP[args['image']]
	region_id = REGION_ID_MAP[args['region']]

	try:
		do = DoManager(args['client_id'], args['api_key'])
		do.new_droplet(hostname, size, image_id, region_id, virtio=True, private_networking=True)
		
		return 0
					
	except Exception as e:
		print(e)
		return 1

	return 0

if __name__ == '__main__':
	sys.exit(main())
