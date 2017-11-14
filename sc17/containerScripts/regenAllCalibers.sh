#!/bin/bash

for i in 190 191 192 194 200 201
do
	scp senderRegen.sh rootnh@192.168.120.$i:~/
	ssh rootnh@192.168.120.$i ./senderRegen.sh
done
