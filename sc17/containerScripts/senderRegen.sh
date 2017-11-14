#!/bin/bash

# Creates files on the DTN if they don't exist already
# Assumes the existence of a /storage/ directory
# From the jupyter notebook declaring file sizes:
# buckets=[30*1024,15*1024,10*1024,5*1024,1*1024,512,128]

#Set MTU to 9000
ifconfig eth1 mtu 9000

#Create files

if [ ! -e "/storage/2048.img" ]
then
	dd if=/dev/zero of=/storage/2048.img bs=1M count=2048
	chmod +r /storage/2048.img
fi

if [ ! -e "/storage/5120.img" ]
then
	dd if=/dev/zero of=/storage/5120.img bs=1M count=5120
	chmod +r /storage/5120.img
fi

if [ ! -e "/storage/10240.img" ]
then
	dd if=/dev/zero of=/storage/10240.img bs=1M count=10240
	chmod +r /storage/10240.img
fi

# Brute force reset maxrate
tc qdisc del dev eth1 root
tc qdisc add dev eth1 root fq

# Start an iperf3 server for fun
iperf3 -sD
