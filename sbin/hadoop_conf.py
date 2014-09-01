#!/usr/bin/python3

import os, sys

HADOOP_CONFIG_VALUES = {
	'2': {
		'map_task': 2,
		'reduce_task': 1,
		'heap': 1536,
		'task_heap': 1024,
	},
	'4': {
		'map_task': 4,
		'reduce_task': 3,
		'heap': 1536,
		'task_heap': 1024,
	},
	'8': {
		'map_task': 8,
		'reduce_task': 6,
		'heap': 1792,
		'task_heap': 1536,
	},
	'12': {
		'map_task': 12,
		'reduce_task': 10,
		'heap': 2560,
		'task_heap': 2048,
	},
	'16': {
		'map_task': 16,
		'reduce_task': 12,
		'heap': 2560,
		'task_heap': 2048,
	},
}

def printConfig(droplet_size):
	config = HADOOP_CONFIG_VALUES[droplet_size] if droplet_size in HADOOP_CONFIG_VALUES else None

	if config:
		# heap max, map task max, reduce task max, task heap max
		print('%d\t%d\t%d\t%d' % (config['map_task'], config['reduce_task'], config['heap'], config['task_heap']))
	else:
		raise ValueError('shoo!!')
		
def printHelp():
	print('boo!!')

def main():
	if 2 == len(sys.argv):
		printConfig(sys.argv[1])
		return 0
	else:
		printHelp()
		return 1

if __name__ == '__main__':
	sys.exit(main())
