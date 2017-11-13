#!/bin/bash

ssh rootnh@192.168.120.190 tc qdisc add dev eth1 root fq

for i in 100 200 300 400 500
do
	ssh rootnh@192.168.120.190 << EOF 
tc qdisc change dev eth1 root fq maxrate ${i}Mbit
iperf3 -c 192.168.112.201
EOF
done

ssh rootnh@192.168.120.190 tc qdisc add dev eth1 root fq
