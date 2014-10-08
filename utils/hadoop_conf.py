#!/usr/bin/python3

import os, sys

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

def printConfig(droplet_size, node_count):
	config = HADOOP_CONFIG_VALUES[droplet_size] if droplet_size in HADOOP_CONFIG_VALUES else None

	if config:
		# 
		print(("{container_heap_max} {map_task_heap_max} {reduce_task_heap_max}"
						" {map_jvm_heap_max} {reduce_jvm_heap_max}"
						" {map_task_per_node} {reduce_task_per_node}"
						" {map_task_total} {reduce_task_total}")
						.format(map_task_total = config['map_task_per_node'] * node_count,
						reduce_task_total = config['reduce_task_per_node'] * node_count, **config))
	else:
		raise ValueError('shoo!!')
		
def printHelp():
	print('python3 hadoop_conf.py <core-count> <node-count>')

def main():
	if 3 == len(sys.argv):
		printConfig(int(sys.argv[1]), int(sys.argv[2]))
		return 0
	else:
		printHelp()
		return 1

if __name__ == '__main__':
	sys.exit(main())
