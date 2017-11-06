#!/bin/bash

# Creates files on the DTN if they don't exist already
# Assumes the existence of a /storage/ directory
# From the jupyter notebook declaring file sizes:
# buckets=[30*1024,15*1024,10*1024,5*1024,1*1024,512,128]

#Set MTU to 9000
ifconfig eth1 mtu 9000

#Create files
if [ ! -e "/storage/128.img" ]
then
	dd if=/dev/zero of=/storage/128.img bs=1M count=128
	chmod +r /storage/128.img
fi

if [ ! -e "/storage/512.img" ]
then
	dd if=/dev/zero of=/storage/512.img bs=1M count=512
	chmod +r /storage/512.img
fi

if [ ! -e "/storage/1024.img" ]
then
	dd if=/dev/zero of=/storage/1024.img bs=1M count=1204
	chmod +r /storage/1024.img
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

if [ ! -e "/storage/15360.img" ]
then
	dd if=/dev/zero of=/storage/15360.img bs=1M count=15360
	chmod +r /storage/15360.img
fi

if [ ! -e "/storage/30720.img" ]
then
	dd if=/dev/zero of=/storage/30720.img bs=1M count=30720
	chmod +r /storage/30720.img
fi

# Brute force reset maxrate
tc qdisc del dev eth1 root
tc qdisc add dev eth1 root fq

# Start an iperf3 server for fun
iperf3 -sD

