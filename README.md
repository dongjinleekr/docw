docw (ver. 0.5)
===============

DOCW is a cli-based tool for building JIT cluster on top of DigitalOcean™ cloud service. Using this tool, you can deploy your own hadoop cluster easily & quickly.

# Prerequisitives #

* python 3 with psutil, dopy package.

# Quickstart #

## Creating hadoop cluster in 5 minutes ##

> docw mknodes 4 2	\# create 2 nodes, each of which has 4 cores.

This command creates droplets for your digitalocean account. Be sure that you have enough droplet limit, whose default value is 5. If you request for more droplets, admins will raise your limit. Wait until all created droplets are active and temporary passwords are delivered to your email.

Hostnames are given automatically using your username. For example, if your unix username is 'joker', docw will create hosts named with joker-0, joker-1, ... and so on. In my case, it was 'dongjinleekr'.

> docw format --all

This command conducts following works, for each droplet:

1. Reset root password: by default, 'root_password'.
2. Add hostname-ip address mapping to your /etc/hosts.
3. Install basic packages, e.g. nscd.
4. Add user account. by default, 'hduser' / 'hduser'.
5. Establish loginless connection between your machine and the created host.

By following command, hadoop cluster is completed:

> docw mkcluster testhd hadoop ${USER}-0 ${USER}-1	\# configure hadoop cluster, whose master node would be ${USER}-0

After above command completed, connect to master node and run hadoop cluster:

> ssh hduser@${USER}-0
> boot-all

Now, you have a hadoop cluster consists of ${USER}-0 and ${USER}-1.

## Creating zookeeper cluster in 5 minutes ##

Creating zookeeper cluster is also easy.

> docw mknodes 2 3

> docw format --all

> docw mkcluster testzk zookeeper ${USER}-2 ${USER}-3 ${USER}-4

If you want to use created zookeeper cluster from created hadoop cluster, bond two clusters:

> docw merge testzk testhd testcl

## Removing Cluster

After use, delete the whole cluster:

> docw rmcluster testhd
> docw rmcluster testzk

## Future Plans

In version 0.6, following features will be supported:

1. Boilerplated arguments processing.
2. Spark support.
3. Automated prerequisitives configuration.
4. Code refine.
5. More documentations.

If you have any questions or proposes, don't hesitate to contact me: dongjin.lee.kr@gmail.com.

Thanks a lot!
