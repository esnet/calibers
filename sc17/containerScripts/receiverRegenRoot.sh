#!/bin/bash

# Run as root

# Remove spurious qdiscs
tc qdisc del dev eth1 root
tc qdisc show dev eth1 root

# Make /storage accessible by all for globus
chmod -R 777 /storage

# Start an iperf3 server for fun
iperf3 -sD
