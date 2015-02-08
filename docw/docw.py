'''
Created on Jan 27, 2015

@author: dongjinleekr
'''

import sys, os, importlib

import digitalocean as do

def printHelp():
  helpMsg = 'Usage: docw (create|destroy) [command-args]'
  print(helpMsg)

default_config = {
  'username': os.environ['USER'],
  'image': 'ubuntu-14-04-x64',
  'token': 'API_TOKEN_NOT_SPECIFIED',
  'region': 'sfo1',
  'timezone': 'US/Pacific',
  'install': 'opt',
  'ssh-dir': os.path.expanduser('~/.ssh'),
  # package versions
  'version.hadoop': '2.5.2',
  'version.zookeeper': '3.4.6',
  # package repositories: different from droplet region.
  # for details, see: http://www.apache.org/mirrors/
  # hadoop
  'repository.hadoop.nyc1': 'http://www.gtlib.gatech.edu/pub/apache/hadoop/common/',
  'repository.hadoop.nyc2': 'http://www.gtlib.gatech.edu/pub/apache/hadoop/common/',
  'repository.hadoop.nyc3': 'http://www.gtlib.gatech.edu/pub/apache/hadoop/common/',
  'repository.hadoop.sfo1': 'http://www.gtlib.gatech.edu/pub/apache/hadoop/common/',
  'repository.hadoop.lon1': 'http://mirror.vorboss.net/apache/hadoop/common/',
  'repository.hadoop.sgp1': 'http://mirror.nus.edu.sg/apache/hadoop/common/',
  'repository.hadoop.ams1': 'http://apache.proserve.nl/hadoop/common/',
  'repository.hadoop.ams2': 'http://apache.proserve.nl/hadoop/common/',
  'repository.hadoop.ams3': 'http://apache.proserve.nl/hadoop/common/',
  # zookeeper
  'repository.zookeeper.nyc1': 'http://www.gtlib.gatech.edu/pub/apache/zookeeper/',
  'repository.zookeeper.nyc2': 'http://www.gtlib.gatech.edu/pub/apache/zookeeper/',
  'repository.zookeeper.nyc3': 'http://www.gtlib.gatech.edu/pub/apache/zookeeper/',
  'repository.zookeeper.sfo1': 'http://www.gtlib.gatech.edu/pub/apache/zookeeper/',
  'repository.zookeeper.lon1': 'http://mirror.vorboss.net/apache/zookeeper/',
  'repository.zookeeper.sgp1': 'http://mirror.nus.edu.sg/apache/zookeeper/',
  'repository.zookeeper.ams1': 'http://apache.proserve.nl/zookeeper/',
  'repository.zookeeper.ams2': 'http://apache.proserve.nl/zookeeper/',
  'repository.zookeeper.ams3': 'http://apache.proserve.nl/zookeeper/',
}

DEFAULT_DOCW_CONF_DIR = os.path.expanduser('~/.docw')
DEFAULT_DOCW_CONF_FILE = os.path.join(DEFAULT_DOCW_CONF_DIR, 'config.cfg')

USER_SETTINGS_TEMPLATE = '''# Digitalocean api (v2) token.
# For details, see here: https://www.digitalocean.com/community/tutorials/how-to-use-the-digitalocean-api-v2
token=

# Droplet Region: (nyc1|nyc2|nyc3|sfo1|lon1|sgp1|ams1|ams2|ams3)
region=sfo1

# Timezone: US/Pacific, Asia/Seoul, ...
timezone=US/Pacific

# Package installation path of each droplet (base: home directory)
install=opt
'''

def read_user_config(path):
  with open(path, 'r') as f:
    return { line.split('=')[0].strip(): line.split('=')[1].strip() for line in f.readlines() if 2 == len(line.split('='))}

def get_user_conf():
  if not os.path.exists(DEFAULT_DOCW_CONF_DIR):
    os.mkdir(DEFAULT_DOCW_CONF_DIR)
    with open(DEFAULT_DOCW_CONF_FILE, 'w') as f:
      f.write(USER_SETTINGS_TEMPLATE)
    raise ValueError("Error: No docw configuration: default config file created. please edit %s" % DEFAULT_DOCW_CONF_FILE)
  
  if not os.path.isdir(DEFAULT_DOCW_CONF_DIR):
    raise ValueError('Error: Can\'t read the default config directory: %s is not a directory.' % DEFAULT_DOCW_CONF_DIR)
  
  if not os.path.exists(DEFAULT_DOCW_CONF_FILE):
    with open(DEFAULT_DOCW_CONF_FILE, 'w') as f:
      f.write(USER_SETTINGS_TEMPLATE)
    raise ValueError("Error: No docw configuration: default config file created. please edit %s" % DEFAULT_DOCW_CONF_FILE)

  user_config = read_user_config(DEFAULT_DOCW_CONF_FILE)
  config = dict(default_config, **user_config)
  
  # validate token & region
  mngr = do.Manager(token=config['token'])
  regions = set([ region.slug for region in mngr.get_all_regions() ])
  
  if config['region'] not in regions:
    raise ValueError("Error: Invalid region - %s" % config['region'])
  
  config['public_key_path'] = os.path.join(config['ssh-dir'], 'id_rsa.pub')
  config['private_key_path'] = os.path.join(config['ssh-dir'], 'id_rsa')
  config['known_hosts_path'] = os.path.join(config['ssh-dir'], 'known_hosts')
  
  with open(config['public_key_path']) as file:
    config['public-key'] = file.read().strip()
  
  with open(config['private_key_path']) as file:
    config['private-key'] = file.read().strip()
  
  return config

COMMANDS = { 'create', 'destroy' }

def main():
  if len(sys.argv) < 2:
    print('Error: no command specified', file=sys.stderr)
    return 1
  
  command = sys.argv[1]
  user_conf = get_user_conf()
  
  module = importlib.import_module('docw.{module}'.format(module=command))
  func = getattr(module, 'process')
  return func(user_conf, sys.argv[2:])

if __name__ == '__main__':
  sys.exit(main())