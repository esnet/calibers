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
        dest = request.form['dest']
        subprocess.Popen(('globus-url-copy -p 1 file:///storage/'+size+'.img ftp://'+dest).split())
        time.sleep(.4) # Wait for the connection to establish
        output = subprocess.check_output('ss -int'.split())
        return output

api.add_resource(FileTransfer, '/<string:size>')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
