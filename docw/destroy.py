import json, os, shutil, tempfile

from contextlib import closing

import digitalocean as do

def update_ssh_hashes(known_hosts_path, ssh_hashes):
  with open(known_hosts_path, 'rt') as f:
    g_fd, g_path = tempfile.mkstemp()
    with closing(os.fdopen(g_fd, 'wt')) as g:
      for ssh_hash in f.readlines():
        if ssh_hash.strip() not in ssh_hashes:
          g.write(ssh_hash)
          
  shutil.move(g_path, known_hosts_path)

def update_hosts(hostname_to_ips):
  '''
  Remove given hostname-ip set from /etc/hosts.
  '''
  to_remove_list = [ '%s %s' % (ip, hostname) for hostname, ip in hostname_to_ips.items() ]
  with open('/etc/hosts', 'rt') as f:
    g_fd, g_path = tempfile.mkstemp()
    with closing(os.fdopen(g_fd, 'wt')) as g:
      for ip_host in f.readlines():
        if ip_host.strip() not in to_remove_list:
          g.write(ip_host)

  os.system('sudo mv %s /etc/hosts' % g_path)
  os.system('sudo service nscd restart')

def process(user_conf, args):
  cluster_desc_file = os.path.abspath(args[0])
  with open(cluster_desc_file) as f:
    cluster_desc = json.loads(f.read())
  
  # update ~/.ssh/known_hosts
  update_ssh_hashes(user_conf['known_hosts_path'],
                    [ ssh_hash for host_desc in cluster_desc.values() if 'ssh_hashes' in host_desc
                      for ssh_hash in host_desc['ssh_hashes'] ])
  
  # update /etc/hosts
  update_hosts({ hostname: host_desc['ip'] for hostname, host_desc in cluster_desc.items() })
  
  # destroy droplets
  droplet_ids = set([ host_desc['id'] for host_desc in cluster_desc.values() ])
  mngr = do.Manager(**user_conf)
  
  for droplet in mngr.get_all_droplets():
    if droplet.id in droplet_ids:
      droplet.destroy()

  # remove
  os.remove(cluster_desc_file)