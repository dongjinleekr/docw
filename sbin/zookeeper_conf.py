#!/usr/bin/python3

import os, sys

CFG_TEMPLATE = '''# The number of milliseconds of each tick
tickTime=2000
 
# The number of ticks that the initial synchronization phase can take
initLimit=10
 
# The number of ticks that can pass between 
# sending a request and getting an acknowledgement
syncLimit=5
 
# the directory where the snapshot is stored.
# Choose appropriately for your environment
dataDir={data_dir}

# the port at which the clients will connect
clientPort=2181

# the directory where transaction log is stored.
# this parameter provides dedicated log device for ZooKeeper
dataLogDir={log_dir}
 
# ZooKeeper server and its port no.
# ZooKeeper ensemble should know about every other machine in the ensemble
# specify server id by creating 'myid' file in the dataDir
# use hostname instead of IP address for convenient maintenance
{entries}'''

def printConfig(datadir, logdir, hostnames):
	zk_entries = [ 'server.{id}={hostname}:2888:3888'.format(id = k + 1, hostname = v) for (k, v) in enumerate(hostnames) ]

	print(CFG_TEMPLATE.format(data_dir = datadir, log_dir = logdir, entries = '\n'.join(zk_entries)))
	
def printHelp():
	print('python3 zookeeper_conf.py <hostname>*')

def main():
	if len(sys.argv) > 1:
		printConfig(sys.argv[1], sys.argv[2], sys.argv[3:])
		return 0
	else:
		printHelp()
		return 1

if __name__ == '__main__':
	sys.exit(main())
