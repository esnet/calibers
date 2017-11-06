#!/bin/bash

# Needs to be run as a vanilla user
/usr/sbin/globus-gridftp-server -S -p 8192 -data-interface 192.168.100.192 -aa -home-dir /

