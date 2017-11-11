#!/bin/bash

# Needs to be run as a vanilla user
/usr/sbin/globus-gridftp-server -S -p 8201 -data-interface 192.168.100.201 -aa -home-dir /

