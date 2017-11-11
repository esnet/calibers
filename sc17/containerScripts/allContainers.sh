#!/bin/bash

for i in 111 112 113 114 115 116
do
	ssh rootnh@192.168.120.$i rm /storage/*.img
done
