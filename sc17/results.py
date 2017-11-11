#!/usr/bin/env python

import re, glob

for path in glob.glob('*.log'):
	print '\n',path
	with open(path,'r') as fp:
		for line in fp:
			start = float(re.compile('START=\d+.\d+').search(line).group(0)[6:])
			end = float(re.compile('DATE=\d+.\d+').search(line).group(0)[5:])
			print end-start
