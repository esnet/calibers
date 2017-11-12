#!/bin/bash
# To be run from 118

foi i in 111 112 113 114 115 116
do
	iperf3 -Rc 192.168.200.$i
done
