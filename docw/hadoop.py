#!/usr/bin/python3

from lxml import etree as et

HADOOP_CONFIG_VALUES = {
  '4gb': {
    'container_heap_max': 2048,
    'map_task_heap_max': 1024,
    'reduce_task_heap_max': 1024,
    'map_jvm_heap_max': 896,
    'reduce_jvm_heap_max': 896,
    'map_task_per_node': 2,
    'reduce_task_per_node': 2,
  },
  '8gb': {
    'container_heap_max': 4096,
    'map_task_heap_max': 1024,
    'reduce_task_heap_max': 1024,
    'map_jvm_heap_max': 896,
    'reduce_jvm_heap_max': 896,
    'map_task_per_node': 4,
    'reduce_task_per_node': 4,
  },
  '16gb': {
    'container_heap_max': 8192,
    'map_task_heap_max': 1024,
    'reduce_task_heap_max': 1024,
    'map_jvm_heap_max': 896,
    'reduce_jvm_heap_max': 896,
    'map_task_per_node': 8,
    'reduce_task_per_node': 8,
  },
}

INSTALLER_TEMPLATE = '''# Make directory

mkdir -p $(dirname {install_path})

# Download & Install

wget {repository}/hadoop-{version}/hadoop-{version}.tar.gz
tar -xvf hadoop-{version}.tar.gz
mv hadoop-{version} {install_path}
rm hadoop-{version}.tar.gz
cp /usr/lib/libsnappy.so {install_path}/lib/native/

sed -i -e '/^export\ JAVA_HOME/s/^.*$/export\ JAVA_HOME=\/usr\/lib\/jvm\/java-7-oracle/' {install_path}/etc/hadoop/hadoop-env.sh

# Set env variables

echo '' >> ${{HOME}}/.bashrc
echo "export HADOOP_PREFIX={install_path}" >> ${{HOME}}/.bashrc
echo 'export HADOOP_CONF_DIR=${{HADOOP_PREFIX}}/etc/hadoop' >> ${{HOME}}/.bashrc
echo 'export HADOOP_MAPRED_HOME=${{HADOOP_PREFIX}}' >> ${{HOME}}/.bashrc
echo 'export HADOOP_COMMON_HOME=${{HADOOP_PREFIX}}' >> ${{HOME}}/.bashrc
echo 'export HADOOP_HDFS_HOME=${{HADOOP_PREFIX}}' >> ${{HOME}}/.bashrc
echo 'export HADOOP_YARN_HOME=${{HADOOP_PREFIX}}' >> ${{HOME}}/.bashrc
echo '' >> ${{HOME}}/.bashrc
echo 'export PATH=$PATH:${{HADOOP_PREFIX}}/bin:${{HADOOP_PREFIX}}/sbin' >> ${{HOME}}/.bashrc'''

def toXML(props):
  root_node = et.Element('configuration')
  
  for key in props.keys():
    pNode = et.SubElement(root_node, 'property')
    et.SubElement(pNode, 'name').text = key
    et.SubElement(pNode, 'value').text = props[key]
  
  return str(et.tostring(et.ElementTree(root_node), xml_declaration=True, pretty_print=True, encoding='utf-8'), 'utf-8')

def core_site_config(**props):
  return toXML({ 'fs.defaultFS': 'hdfs://{master}:9000'.format(**props),
                'io.compression.codecs': 'org.apache.hadoop.io.compress.SnappyCodec',
  })

def mapred_site_config(**props):
  return toXML({ 'mapreduce.framework.name': 'yarn'.format(**props),
                'mapreduce.jobtracker.address': '{master}:54311'.format(**props),
                'mapreduce.map.memory.mb': '{map_task_heap_max}'.format(**props),
                'mapreduce.reduce.memory.mb': '{reduce_task_heap_max}'.format(**props),
                'mapreduce.map.java.opts': '-Xmx{map_jvm_heap_max}m'.format(**props),
                'mapreduce.reduce.java.opts': '-Xmx{reduce_jvm_heap_max}m'.format(**props),
                'mapreduce.job.maps': '{map_task_per_node}'.format(**props),
                'mapreduce.job.reduces': '{reduce_task_per_node}'.format(**props),
                'mapreduce.tasktracker.map.tasks.maximum': '{map_task_total}'.format(**props),
                'mapreduce.tasktracker.reduce.tasks.maximum': '{reduce_task_total}'.format(**props),
  })

def hdfs_site_config(**props):
  return toXML({ 'dfs.replication': '3',
                'dfs.secondary.http.address': '{master}:50090'.format(**props),
                'dfs.permissions': 'false'.format(**props),
  })

def yarn_site_config(**props):
  return toXML({ 'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
                'yarn.nodemanager.aux-services.mapreduce.shuffle.class': 'org.apache.hadoop.mapred.ShuffleHandler',
                'yarn.nodemanager.resource.memory-mb': '{container_heap_max}'.format(**props),
                'yarn.resourcemanager.resource-tracker.address': '{master}:8025'.format(**props),
                'yarn.resourcemanager.scheduler.address': '{master}:8030'.format(**props),
                'yarn.resourcemanager.address': '{master}:8040'.format(**props),
  })

def system_packages_cmds():
  return '''apt-get update
apt-get -y install build-essential software-properties-common python-software-properties
apt-get -y install nscd bc screen python3-pip libxml2-dev libxslt1-dev zlib1g-dev
apt-get -y install libsnappy1 libsnappy-dev

# install java
add-apt-repository -y ppa:webupd8team/java
apt-get update
echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections
echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections
apt-get -y --force-yes install oracle-java7-installer oracle-java7-set-default'''

def user_packages_cmds(**props):
  return INSTALLER_TEMPLATE.format(**props)