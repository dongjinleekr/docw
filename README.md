docw
====

DOCW is a cli-based tool for building JIT cluster on top of DigitalOcean™ cloud service. Using this tool, you can deploy your own hadoop cluster easily & quickly.

## Create Node(s)

With following syntax, you can create a node on your digitalocean account:

Syntax:

> docw mknode \<size\>

Example:

> docw mknode 4  \# create a node, with 4 cores.

Hostnames are given automatically using your username. For example, if your unix username is 'joker', docw will create hosts named with joker-0, joker-1, ... and so on. In my case, it is 'dongjinleekr'.

You can also create multiple nodes at once:

Syntax:

> docw mknodes \<size\> \<count\>

Example:

> docw mknodes 2 3  \# Create 3 hosts at once, each of which has 2 cores.

## Format Node(s)

When a digitalocean node is created, its root password is ramdonly generated and delivered via your email account. Before using it, you have to complete following tasks:

1. reset root password: by default, 'root_password'.
2. add hostname-ip address mapping to your local /etc/hosts.
3. establish loginless connection between your local machine and the node.
4. install basic packages, e.g. nscd.

You can do all above tasks at once, with following command:

Syntax:

> docw format \<hostname\>*

Example:

> docw format dongjinleekr-0 dongjinleekr-1 dongjinleekr-2

When the job completes, check your /etc/hosts. You can see all the host we made so far are added to your hosts file. You can also connect to each of them using **ssh root@<hostname>**.

## Make Cluster

Now You can create cluster with formatted hosts. By version 0.5, docw only supports hadoop 1.2.1.

Syntax:

> docw mkcluster \<cluster-name\> \<role\> \<hostname\>*

Example:

> docw mkcluster hdcluster hadoop dongjinleekr-1 dongjinleekr-2  \# create hadoop cluster named 'hdcluster',  using two formatted nodes. dongjinleekr-1 becomes namenode.

let's connect to namenode and launch hadoop cluster:

> ssh hduser@dongjinleekr-1
> 
> hadoop namenode -format
> 
> start-all.sh

## Querying Cluster

Using docw, you can create & manage multiple clusters, with different names. To check the information about any cluster, please input **docw ls \<cluster\>**. Using **docw ls --all**, you can see the whole list of running clusters.

## Remove Cluster

After use, delete the whole cluster:

Syntax:

> docw rmcluster \<cluster-name\>

Example:

> docw rmcluster hdcluster
