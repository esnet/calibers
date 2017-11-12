#!/bin/bash
# To be run from 117

foi i in 190 191 192 194 200 201
do
	iperf3 -Rc 192.168.112.$i
done
