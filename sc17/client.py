#!/usr/bin/env python

#Better name: sender.py

import time
import datetime
import subprocess
import re
import json
from flask import Flask, request
from flask_restful import Resource, Api
app = Flask(__name__)
api = Api(app)


import socket
import fcntl
import struct

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

@app.route('/setrate/<rate>')
def setRate(rate):
    try:
        subprocess.check_call(('tc qdisc change dev eth1 root fq maxrate '+rate).split())
    except subprocess.CalledProcessError as e:
        print e
    outRate = subprocess.check_output('tc -i qdisc show dev eth1'.split())
    outRate = re.findall('maxrate \d+',outRate)[0]
    outRate = re.findall('\d+',outRate)[0]
    return outRate
    
class FileTransfer(Resource):
    def put(self, size):
        #dest = request.json['dest']
        #print "got request: " + dest
        tmp = size.split('-')
        size = tmp[0]
        dest = tmp[1]
        file = tmp[2]
        subprocess.Popen(('globus-url-copy -vb -fast -p 1 file:///storage/'+size+' ftp://'+dest+":9002/data/" + file).split())
        time.sleep(.4) # Wait for the connection to establish
        output = subprocess.check_output('ss -int'.split())
        return output

api.add_resource(FileTransfer, '/start/<string:size>')

if __name__ == '__main__':
    app.run(host=get_ip_address('eth0'))
