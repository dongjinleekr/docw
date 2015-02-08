import importlib, json, os, tempfile, threading, time

from contextlib import closing
import itertools as it

import digitalocean as do
import pexpect as pe
import paramiko as pm
import scp

from docw import hadoop as hd
from docw import zookeeper as zk

ROLE_ORDER = [ 'hadoop', 'zookeeper' ]
SIZE_SLUG_ORDER = [ '512mb', '1gb', '2gb', '4gb', '8gb', '16gb' ]
CLOUDCONFIG_TEMPLATE = """#cloud-config

users:
  - name: {username}
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh-authorized-keys:
      - {public-key}

timezone: {timezone}"""
SSH_NEWKEY_MSG = 'Are you sure you want to continue connecting (yes/no)?'
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')

def get_droplet_name(cluster_name, index):
  return '%s-%d' % (cluster_name, index)

def get_user_data(settings):
  return CLOUDCONFIG_TEMPLATE.format(**settings)

def get_size_slugs(cluster_conf, role):
  """
  Returns list of size_slug required for given cluster_conf and role, in decreasing order.
  """
  ret = []
  for hosts in (hosts for group in cluster_conf if role == group['role'] for hosts in group['hosts']):
    for _ in range(0, hosts['count']):
      ret.append(hosts['size'])

  ret.sort(key=lambda x: SIZE_SLUG_ORDER.index(x))
  ret.reverse()
  
  return ret

def get_host_settings(user_conf, cluster_name, cluster_conf):
  """
  Returns list of droplet settings and dict of host configs.
  
  ex) ([
        {
          name: 'droplet-0',
          size_slug: '4096mb',
          ssh_keys: [ xxxx ],
          user_data: 'xxxx',
        },
        {
          name: 'droplet-1',
          size_slug: '8192mb',
          ssh_keys: [ xxxx ],
          user_data: 'xxxx',
        }
      ],
      {
        'droplet-0': {
          'role': 'hadoop',
          'install_path': xxx,
          'repository': xxx,
          'version': xxx,
          'config': {
            '/home/dongjinleekr/opt/hadoop/etc/hadoop/core-site.xml': '...',
            '/home/dongjinleekr/opt/hadoop/etc/hadoop/mapred-site.xml': '...',
            ...
          }
        },
        'droplet-1': {
          'role': 'hadoop',
          'install_path': xxx,
          'repository': xxx,
          'version': xxx,
          'config': {
            '/home/dongjinleekr/opt/hadoop/etc/hadoop/core-site.xml': '...',
            '/home/dongjinleekr/opt/hadoop/etc/hadoop/mapred-site.xml': '...',
            ...
          }
        },
      })
    
  Args:
    @type user_conf: dict
    @param user_conf: user configuration.
    
    @type cluster_name: str
    @param cluster_name: 
    
    @type cluster_conf: listret
    @param cluster_conf: 

  Returns:
    @return: pair of dict
  """
  
  droplet_settings = []
  host_configs = dict()
  user_data = get_user_data(user_conf)
  roles = set([ group['role'] for group in cluster_conf ])
  
  counter = it.count(0)
  for role in sorted(roles, key=lambda r: ROLE_ORDER.index(r)):
    size_slugs = get_size_slugs(cluster_conf, role)
    install_path = os.path.join('/', 'home', user_conf['username'], user_conf['install'], role)
    repository = user_conf['repository.%s.%s' % (role, user_conf['region'])]
    version = user_conf['version.%s' % role]
    
    if 'hadoop' == role:
      # create dedicated master host
      size_slugs.insert(0, '4gb')
      hd_droplet_settings = [ { 'name': get_droplet_name(cluster_name, next(counter)),
                                'image': user_conf['image'],
                                'region': user_conf['region'],
                                'timezone': user_conf['timezone'],
                                'size_slug': size_slug,
                                'user_data': user_data,
                           } for size_slug in size_slugs ]
      master_hostname = hd_droplet_settings[0]['name']
      slave_hostnames = [ setting['name'] for setting in hd_droplet_settings[1:] ]
          
      map_task_total = sum([ hd.HADOOP_CONFIG_VALUES[size_slug]['map_task_per_node'] for size_slug in size_slugs[1:] ])
      reduce_task_total = sum([ hd.HADOOP_CONFIG_VALUES[size_slug]['reduce_task_per_node'] for size_slug in size_slugs[1:] ])
      
      config_path = os.path.join(install_path, 'etc', 'hadoop')
      core_site_path = os.path.join(config_path, 'core-site.xml')
      mapred_site_path = os.path.join(config_path, 'mapred-site.xml')
      hdfs_site_path = os.path.join(config_path, 'hdfs-site.xml')
      yarn_site_path = os.path.join(config_path, 'yarn-site.xml')
      master_path = os.path.join(config_path, 'master')
      slaves_path = os.path.join(config_path, 'slaves')
      
      core_site_value = hd.core_site_config(master=master_hostname)
      hdfs_site_value = hd.hdfs_site_config(master=master_hostname)
      master_value = master_hostname
      slaves_value = '\n'.join(slave_hostnames)
    
      hd_host_configs = dict()
      
      for setting in hd_droplet_settings:
        hd_host_configs[setting['name']] = {
          'role': 'hadoop',
          'install_path': install_path,
          'repository': repository,
          'version': version,
          'config': {
            core_site_path: core_site_value,
            mapred_site_path: hd.mapred_site_config(master=master_hostname,
                                                    map_task_total=map_task_total,
                                                    reduce_task_total=reduce_task_total,
                                                    **dict(hd.HADOOP_CONFIG_VALUES[setting['size_slug']])),
            hdfs_site_path: hdfs_site_value,
            yarn_site_path: hd.yarn_site_config(master=master_hostname,
                                                map_task_total=map_task_total,
                                                reduce_task_total=reduce_task_total,
                                                **dict(hd.HADOOP_CONFIG_VALUES[setting['size_slug']])),
            master_path: master_value,
            slaves_path: slaves_value,
          }
      }
      
      droplet_settings.extend(hd_droplet_settings)
      host_configs.update(hd_host_configs)
    elif 'zookeeper' == role:
      # todo: the number of server is odd?
      zk_droplet_settings = [ { 'name': get_droplet_name(cluster_name, next(counter)),
                                'size_slug': size_slug,
                                'user_data': user_data,
                           } for size_slug in size_slugs ]

      zkconfig_path = os.path.join(install_path, 'conf', 'zoo.cfg')
      zkconfig_value = zk.config([ setting['name'] for setting in zk_droplet_settings ])
      
      zk_host_configs = dict()
      for setting in zk_droplet_settings:
        zk_host_configs[setting['name']] = {
          'role': 'zookeeper',
          'install_path': install_path,
          'repository': repository,
          'version': version,
          'config': {
            zkconfig_path: zkconfig_value,
          }
        }

      droplet_settings.extend(zk_droplet_settings)
      host_configs.update(zk_host_configs)

  return droplet_settings, host_configs

def is_droplet_limit_sufficient(mngr, hostnames):
  limit = mngr.get_account().droplet_limit
  exists = len(mngr.get_all_droplets())
  
  return limit - exists >= len(hostnames)

def all_hostnames_available(mngr, hostnames):
  exists = set([ droplet.name for droplet in mngr.get_all_droplets() ])
  
  if set.intersection(exists, set(hostnames)):
    return False
  else:
    return True

def update_hosts(hostname_to_ips):
  '''
  Add given hostname-ip set into /etc/hosts.
  '''
  with open('/etc/hosts', 'rt') as f:
    r = f.read()
    s = '\n'.join([ '%s %s' % (public_ip, hostname) for hostname, public_ip in hostname_to_ips.items() ])
    g_fd, g_path = tempfile.mkstemp()
    with closing(os.fdopen(g_fd, 'wt')) as g:
      g.write(r + s + '\n')

  os.system('sudo mv %s /etc/hosts' % g_path)
  os.system('sudo service nscd restart')

def get_ssh_client():
  client = pm.SSHClient()
  client.load_system_host_keys()
  client.set_missing_host_key_policy(pm.AutoAddPolicy())
  
  return client

def configure_ssh(scp_client, public_key_path, private_key_path, host_hashes_path):
  scp_client.put(public_key_path, './.ssh/')
  scp_client.put(private_key_path, './.ssh/')
  scp_client.put(host_hashes_path, './.ssh/known_hosts')

ETC_HOSTS_TEMPLATE = '''127.0.0.1 localhost

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters

'''

def configure_hosts_file(ssh_client, scp_client, hostname, hostname_to_ips):
  hostnames = sorted(hostname_to_ips.keys(), key=lambda x: int(x[x.index('-') + 1:]))
  hosts_file_content = ETC_HOSTS_TEMPLATE + '\n'.join([ '%s %s' % (hostname_to_ips[hostname], hostname) for hostname in hostnames ]) + '\n'
  
  tmp_fd, tmp_path = tempfile.mkstemp()
  with closing(os.fdopen(tmp_fd, 'wt')) as f:
    f.write(hosts_file_content)
  scp_client.put(tmp_path, 'hosts')
  
  tmp_fd, tmp_path = tempfile.mkstemp()
  with closing(os.fdopen(tmp_fd, 'wt')) as f:
    f.write('mv hosts /etc/hosts')

  scp_client.put(tmp_path, './hosts_conf')
  ssh_client.exec_command("chmod +x ./hosts_conf")
  
  _, stdout, _ = ssh_client.exec_command("sudo ./hosts_conf")
  channel = stdout.channel
  channel.recv_exit_status()

def configure_system_packages(ssh_client, scp_client, commands):
  tmp_fd, tmp_path = tempfile.mkstemp()
  with closing(os.fdopen(tmp_fd, 'wt')) as f:
    f.write(commands)

  scp_client.put(tmp_path, './system_packages_conf')
  ssh_client.exec_command("chmod +x ./system_packages_conf")
  
  _, stdout, _ = ssh_client.exec_command("sudo ./system_packages_conf")
  channel = stdout.channel
  channel.recv_exit_status()

def configure_user_packages(ssh_client, scp_client, commands):
  tmp_fd, tmp_path = tempfile.mkstemp()

  with closing(os.fdopen(tmp_fd, 'wt')) as f:
    f.write(commands)
  
  scp_client.put(tmp_path, './user_packages_conf')
  ssh_client.exec_command("chmod +x ./user_packages_conf")
  
  _, stdout, _ = ssh_client.exec_command("./user_packages_conf")
  channel = stdout.channel
  channel.recv_exit_status()

def configure_user_configs(scp_client, configs):
  for path, contents in configs.items():
    tmp_fd, tmp_path = tempfile.mkstemp()
    with closing(os.fdopen(tmp_fd, 'wt')) as f:
      f.write(contents)
    scp_client.put(tmp_path, path)

def configure_host(hostname, host_config, user_conf, hostname_to_ips, host_hashes_path):
  print('%s: Configuration started.' % hostname)
  ssh_client = get_ssh_client()
  ssh_key = pm.RSAKey.from_private_key_file(user_conf['private_key_path'])
  ssh_client.connect(hostname=hostname,
                     username=user_conf['username'],
                     pkey=ssh_key)
  scp_client = scp.SCPClient(ssh_client.get_transport())
  
  # update ssh files
  start_time = time.time()
  configure_ssh(scp_client, user_conf['public_key_path'], user_conf['private_key_path'], host_hashes_path)
  elapsed_time = time.time() - start_time
  print('%s: updating ./ssh completed: %.2f sec' % (hostname, elapsed_time))
  
  # update /etc/hosts
  start_time = time.time()
  configure_hosts_file(ssh_client, scp_client, hostname, hostname_to_ips)
  elapsed_time = time.time() - start_time
  print('%s: updating /etc/hosts completed: %.2f sec' % (hostname, elapsed_time))
  
  module = importlib.import_module('docw.{module}'.format(module=host_config['role']))
  
  # install system packages
  start_time = time.time()
  commands = getattr(module, 'system_packages_cmds')()
  configure_system_packages(ssh_client, scp_client, commands)
  elapsed_time = time.time() - start_time
  print('%s: Installing system packages completed: %.2f sec' % (hostname, elapsed_time))
  
  # install the package
  start_time = time.time()
  commands = getattr(module, 'user_packages_cmds')(**host_config)
  configure_user_packages(ssh_client, scp_client, commands)
  elapsed_time = time.time() - start_time
  print('%s: Installing user packages completed: %.2f sec' % (hostname, elapsed_time))
  
  # upload config files
  start_time = time.time()
  configure_user_configs(scp_client, host_config['config'])
  elapsed_time = time.time() - start_time
  print('%s: Installing user config files completed: %.2f sec' % (hostname, elapsed_time))

  ssh_client.close()
  print('%s: Configuration completed.' % hostname)

def process(user_conf, args):
  cluster_name = args[0]
  cluster_config = os.path.abspath(args[1])
  with open(cluster_config) as file:
    cluster_settings = json.loads(file.read())
  droplet_settings, host_configs = get_host_settings(user_conf, cluster_name, cluster_settings)
  
  mngr = do.Manager(**user_conf)
  
  # validate
  hostnames = [ setting['name'] for setting in droplet_settings ]

  if False == is_droplet_limit_sufficient(mngr, hostnames):
    raise ValueError('Error: you cannot create %d droplets now.' % len(hostnames))
  
  if False == all_hostnames_available(mngr, hostnames):
    raise ValueError('Error: Duplicated droplet name.')
  
  # create droplets
  hostname_to_droplet_ids = dict()
  for setting in droplet_settings:
    droplet = do.Droplet(token=user_conf['token'],
                          ssh_keys=[ user_conf['public-key'] ],
                          private_ip_address=True,
                          private_networking=True,
                          **setting)
    droplet.create()
    hostname_to_droplet_ids[setting['name']] = droplet.id
  
  # wait until all droplets are activated
  waiting = set(hostname_to_droplet_ids.values())
  print('waiting for new droplets are activated.', end='', flush=True)
  while waiting:
    time.sleep(5)
    print('.', end='', flush=True)
    active_droplet_ids = set([ droplet.id for droplet in mngr.get_all_droplets() if 'active' == droplet.status ])
    waiting = waiting - active_droplet_ids
  print('completed.')
  
  # inspect ip addresses
  hostname_to_ips = dict([ (droplet.name, droplet.ip_address)
                for droplet in mngr.get_all_droplets() if droplet.id in hostname_to_droplet_ids.values() ])
  
  # add to /etc/hosts
  update_hosts(hostname_to_ips)
  
  # write cluster file
  cluster_desc_filename = '%s.json' % cluster_name
  cluster_desc = { hostname: { 'id': hostname_to_droplet_ids[hostname],
                    'ip': hostname_to_ips[hostname] } for hostname in hostnames }
  with open(cluster_desc_filename, 'w') as f:
    json.dump(cluster_desc, f)

  print('cluster description is stored to %s' % cluster_desc_filename)
  
  # add ssh footprint
  hostname_to_ssh_hashes = dict()
  for hostname in hostname_to_ips.keys():
    child = pe.spawn('/usr/bin/ssh-copy-id -i %s %s@%s' % (user_conf['public_key_path'], user_conf['username'], hostname))
    child.expect(SSH_NEWKEY_MSG)
    child.sendline('yes\r')
    child.expect(pe.EOF, timeout=None)
  
    with open(user_conf['known_hosts_path']) as f:
      hostname_to_ssh_hashes[hostname] = [ ssh_hash.strip() for ssh_hash in f.readlines()[-2:]]
      # update cluster file
      cluster_desc[hostname]['ssh_hashes'] = hostname_to_ssh_hashes[hostname]
      with open(cluster_desc_filename, 'w') as g:
        json.dump(cluster_desc, g)

  tmp_hashes_fd, tmp_hashes_path = tempfile.mkstemp()
  with closing(os.fdopen(tmp_hashes_fd, 'wt')) as f:
    f.write('\n'.join([ ssh_hash for ssh_hashes in hostname_to_ssh_hashes.values() for ssh_hash in ssh_hashes ]))

  # do configuration
  threads = [ threading.Thread(target=configure_host,
                               args=(hostname, host_configs[hostname], user_conf, hostname_to_ips, tmp_hashes_path),
                               name=hostname) for hostname in hostname_to_ips.keys() ]
  [ thread.start() for thread in threads ]
  [ thread.join() for thread in threads ]