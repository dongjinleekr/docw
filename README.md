docw (ver. 0.6)
===============

DOCW is a cli tool aimed to building JIT cluster on top of DigitalOcean™ cloud service. Using this tool, you can create & destroy your own cluster easily & quickly.

As of version 0.6, it supports hadoop & zookeeper cluster.

# Prerequisitives

* unix-like system

    I developed & tested it on Ubuntu 14.04 environment.

* python 3
* nscd

    If not, install it by `sudo apt-get -y install nscd`

# Quickstart

## Install

> `sudo python3 setup.py install`

or

> `python3 setup.py install --user`

## Create new cluster

The following command creates a hadoop cluster on your DigitalOcean™ account, consists of 1 master node + [2 slave nodes](https://raw.githubusercontent.com/dongjinleekr/docw/master/template-hadoop-tiny.json). The details of created cluster is stored in [cluster-name].json. (In this case, tinycluster.json)

> `docw create tinycluster template-hadoop-tiny.json`

## Destroy

The following command destroys the hadoop cluster namded 'tinycluster'.

> `docw destroy tinycluster.json`

# Future Plans

In version 0.7, the following features will be supported:

1. Apache Spark, Apache Hama support.
2. 'resume' command: If your cluster creation was terminated un-normally, you don't have to destroy & recreate the cluster any more.

If you have any questions or proposes, don't hesitate to contact me: dongjin.lee.kr@gmail.com.

Thanks a lot!
