#!/bin/bash

for i in 111 112 113 114 115 116 118
do
	ssh rootnh@192.168.120.$i  << EOF
pkill gridftp
globus-gridftp-server -S -p 8$i -data-interface 192.168.200.$i -aa -anonymous-user 'nhanford' -home-dir / -Z ~/$i.log -log-level all
EOF
done
