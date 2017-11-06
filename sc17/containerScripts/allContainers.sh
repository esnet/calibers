#!/bin/bash

for i in 111 112 113 114 115
do
	scp esnetConfig.sh rootnh@192.168.120.$i:~/
	ssh rootnh@192.168.120.$i ./esnetConfig.sh
done
