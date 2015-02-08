#!/usr/bin/python3

import itertools as it

ORDER = [ 'tickTime', 'initLimit', 'syncLimit', 'clientPort' ]

INSTALLER_TEMPLATE = '''# Make directory

mkdir -p $(dirname {install_path})

# Download & Install

wget {repository}/zookeeper-{version}/zookeeper-{version}.tar.gz
tar -xvf zookeeper-{version}.tar.gz
mv zookeeper-{version} {install_path}
rm zookeeper-{version}.tar.gz

# Set env variables

echo '' >> ${{HOME}}/.bashrc
echo "export ZOOKEEPER_INSTALL={install_path}" >> ${{HOME}}/.bashrc
echo '' >> ${{HOME}}/.bashrc
echo 'export PATH=$PATH:${{ZOOKEEPER_INSTALL}}/bin' >> ~/.bashrc'''

def config(hosts):
  args = {
    'tickTime': 2000,
    'initLimit': 10,
    'syncLimit': 5,
    'clientPort': 2181,
  }
  
  oper_conf = '\n'.join([ '%s=%s' % (k, args[k]) for k in sorted(args.keys(), key=lambda x: ORDER.index(x)) ])
  counter = it.count(1)
  server_conf = '\n'.join([ 'server.%d=%s' % (next(counter), host) for host in hosts ])
  
  return oper_conf + '\n\n' + server_conf

def system_packages_cmds():
  return '''apt-get update
apt-get -y install build-essential software-properties-common python-software-properties
apt-get -y install nscd bc screen python3-pip libxml2-dev libxslt1-dev zlib1g-dev

# install java
add-apt-repository -y ppa:webupd8team/java
apt-get update
echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections
echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections
apt-get -y --force-yes install oracle-java7-installer oracle-java7-set-default'''
  
def user_packages_cmds(**props):
  return INSTALLER_TEMPLATE.format(**props)