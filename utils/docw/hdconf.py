#!/usr/bin/python3

import sys, os, tempfile, argparse

from contextlib import closing
from lxml import etree as et

HADOOP_CONFIG_VALUES = {
  4: {
    'container_heap_max': 4096,
    'map_task_heap_max': 1024,
    'reduce_task_heap_max': 1024,
    'map_jvm_heap_max': 896,
    'reduce_jvm_heap_max': 896,
    'map_task_per_node': 4,
    'reduce_task_per_node': 4,
  },
  8: {
    'container_heap_max': 8192,
    'map_task_heap_max': 1024,
    'reduce_task_heap_max': 1024,
    'map_jvm_heap_max': 896,
    'reduce_jvm_heap_max': 896,
    'map_task_per_node': 8,
    'reduce_task_per_node': 8,
  },
}

def toXML(props):
  root_node = et.Element('configuration')
  
  for key in props.keys():
    pNode = et.SubElement(root_node, 'property')
    et.SubElement(pNode, 'name').text = key
    et.SubElement(pNode, 'value').text = props[key]
  
  return et.ElementTree(root_node)

def coreXML(**props):
  return toXML({ 'fs.defaultFS': 'hdfs://{master}:9000'.format(**props),
                'hadoop.tmp.dir': 'file:///home/{user}/var/hadoop/tmp'.format(**props),
                'io.compression.codecs': 'org.apache.hadoop.io.compress.SnappyCodec',
  })

def mapredXML(**props):
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

def hdfsXML(**props):
  return toXML({ 'dfs.replication': '3',
                'dfs.secondary.http.address': '{master}:50090'.format(**props),
                'dfs.permissions': 'false'.format(**props),
                'dfs.datanode.data.dir': 'file:///home/{user}/var/hdfs/datanode'.format(**props),
                'dfs.namenode.name.dir': 'file:///home/{user}/var/hdfs/namenode'.format(**props),
  })

def yarnXML(**props):
  return toXML({ 'yarn.nodemanager.aux-services': 'mapreduce_shuffle',
                'yarn.nodemanager.aux-services.mapreduce.shuffle.class': 'org.apache.hadoop.mapred.ShuffleHandler',
                'yarn.nodemanager.resource.memory-mb': '{container_heap_max}'.format(**props),
                'yarn.resourcemanager.resource-tracker.address': '{master}:8025'.format(**props),
                'yarn.resourcemanager.scheduler.address': '{master}:8030'.format(**props),
                'yarn.resourcemanager.address': '{master}:8040'.format(**props),
  })

def main():
  parser = argparse.ArgumentParser(description='Converts ttxml to wordpress compatible xml.')
  parser.add_argument('-c', '--core', type=int, help='core count.')
  parser.add_argument('-u', '--user', type=str, help='username.')
  parser.add_argument('-m', '--master', type=str, help='master hostname.')
  parser.add_argument('-p', '--map-task-total', type=int, help='total number of map task.')
  parser.add_argument('-q', '--reduce-task-total', type=int, help='total number of reduce task.')
  
  parsed = parser.parse_args(sys.argv[1:])
  args = vars(parsed)
  
  try:
    core_site_xml = coreXML(**dict(HADOOP_CONFIG_VALUES[args['core']], **args))
    
    core_site_fd, core_site_path = tempfile.mkstemp()
    
    with closing(os.fdopen(core_site_fd, 'wb')) as core_site_output:
      # print(et.tostring(core_site_xml, xml_declaration=True, encoding='UTF-8', pretty_print=True))
      core_site_xml.write(core_site_output, xml_declaration=True, encoding='UTF-8', pretty_print=True)
      
    mapred_site_xml = mapredXML(**dict(HADOOP_CONFIG_VALUES[args['core']], **args))
    
    mapred_site_fd, mapred_site_path = tempfile.mkstemp()
    
    with closing(os.fdopen(mapred_site_fd, 'wb')) as mapred_site_output:
      # print(et.tostring(mapred_site_xml, xml_declaration=True, encoding='UTF-8', pretty_print=True))
      mapred_site_xml.write(mapred_site_output, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    
    hdfs_site_xml = hdfsXML(**dict(HADOOP_CONFIG_VALUES[args['core']], **args))
    
    hdfs_site_fd, hdfs_site_path = tempfile.mkstemp()
    
    with closing(os.fdopen(hdfs_site_fd, 'wb')) as hdfs_site_output:
      # print(et.tostring(hdfs_site_xml, xml_declaration=True, encoding='UTF-8', pretty_print=True))
      hdfs_site_xml.write(hdfs_site_output, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    
    yarn_site_xml = yarnXML(**dict(HADOOP_CONFIG_VALUES[args['core']], **args))
    
    yarn_site_fd, yarn_site_path = tempfile.mkstemp()
    
    with closing(os.fdopen(yarn_site_fd, 'wb')) as yarn_site_output:
      # print(et.tostring(yarn_site_xml, xml_declaration=True, encoding='UTF-8', pretty_print=True))
      yarn_site_xml.write(yarn_site_output, xml_declaration=True, encoding='UTF-8', pretty_print=True)
  
    print(' '.join([ core_site_path, mapred_site_path, hdfs_site_path, yarn_site_path ]))
  
  except Exception as e:
    print(e)
    return 1

  return 0

if __name__ == '__main__':
    sys.exit(main())