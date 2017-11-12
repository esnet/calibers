#!/bin/bash

for i in 111 112 113 114 115 116 117 118 190 191 192 194 200 201
do
	ssh rootnh@192.168.120.$i tc qdisc del dev eth1 root
done
