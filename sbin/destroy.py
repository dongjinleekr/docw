#!/usr/bin/python3
'''
Created on Mar 26, 2014

@author: dongjinleekr
'''

import sys, argparse
from dopy.manager import DoManager

def parse(args):
    parser = argparse.ArgumentParser(description='destroy droplet')
    parser.add_argument('-c', '--client_id', type=str, help='client id')
    parser.add_argument('-k', '--api_key', type=str, help='api key')
    parser.add_argument('-n', '--hostname', type=str, help='host name')

    parsed = parser.parse_args(args)

    return vars(parsed)

def main():
  args = parse(sys.argv[1:])

  try:
    do = DoManager(args['client_id'], args['api_key'])
    
    e = next((droplet for droplet in do.all_active_droplets() if droplet['name'] == args['hostname']), None)
    
    if e:
      do.destroy_droplet(e['id'])
    else:
    	raise ValueError('No host named %s' % args['hostname'])
  except:
    return 1

  return 0

if __name__ == '__main__':
    sys.exit(main())
