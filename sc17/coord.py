import pickle
import threading
import time
import datetime
import requests
import numpy as np
from flask import Flask, request
from flask_restful import Resource, Api
from flask_restful import reqparse


import scheduler

class Switch:
    def __init__(self, name, ip, port, vfc, ofport, rtt, token_file=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.vfc = vfc
        self.ofport = ofport
        self.rtt = rtt
        self.token_file = token_file
        if self.token_file != None:
        	f = open(self.token_file)
        	self.token = f.read()
        	f.close()
        else:
        	self.token = None

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()

    def set_rate(self, rate, burst_factor=1):
        # Requested rate is in bps, switch needs CIR in kbps
        # Take ceiling in kbps to ensure we don't meter under rate
        self.requested_cir = int((rate + 1000)/1000)
        # Set CBS to bandwidth-delay product (conservative value) kbps x msec = bits / 8000 = kbytes
        # Multiply by burst_factor to enable reducing CBS, if desired
        self.cbs = int((self.requested_cir * self.rtt / 8000 )* burst_factor)
        self.cbs = max(self.cbs, 10) # 10kbytes minimum burst (must be larger than MTU)
        # Build URL for switch VFC port
        url="https://" + self.ip + "/api/v1/bridges/" + self.vfc + "/tunnels/" + str(self.ofport)
        auth = self.token
        headers={"Authorization":auth,"Content-Type":"application/json"}
        body = '[{"op":"replace","path":"/meter/cir","value":' + str(self.requested_cir) + '},{"op":"replace","path":"/meter/cbs","value":' + str(self.cbs) + '}]'
        r = requests.patch(url, headers=headers, data=body, verify=False)
        if r.status_code != 204:
            print ("Error: Switch.set_rate() returned ", r.status_code, " for ", self)
        
    def get_rate(self):
        url="https://" + self.ip + "/api/v1/bridges/" + self.vfc + "/tunnels/" + str(self.ofport)
        auth = self.token
        headers={"Authorization":auth,"Content-Type":"application/json"}
        r = requests.get(url, headers=headers, verify=False)
        if r.status_code == 200:
            robj = json.loads(r.content)
            self.actual_cir = robj['meter']['cir']
            return robj
        else:
            print ("Error: Switch.get_rate() returned ", r.status_code," for ", self)
            return None
        # if ret = switch.get_rate() && ret != None
        # CIR is ret['meter']['cir']
        # CBS is ret['meter']['cbs']
        
    def get_stats(self):
        url="https://" + self.ip + "/api/v1/stats/tunnels?bridge=" + self.vfc + "&ofport=" + str(self.ofport)
        auth = self.token
        headers={"Authorization":auth,"Content-Type":"application/json"}
        r = requests.get(url, headers=headers, verify=False)
        if r.status_code == 200:
            return json.loads(r.content)
        else:
            print ("Error: Switch.get_stats() returned ", r.status_code," for ", self)
            return None
        # if ret = switch.get_stats() && ret != None
        # RX bytes    is ret['stats'][0]['rx_bytes']
        # Green bytes is ret['stats'][0]['green_bytes']
        # Red bytes   is ret['stats'][0]['red_bytes']


class DTN:
    def __init__(self, name, ip, port, bias_fun=None, bias_args=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.bias_fun = bias_fun
        self.bias_args = bias_args
        self.requests = []
        self.current_request_index = -1
        self.current_request = None

    def get_next_request(self):
		self.current_request_index += 1
		self.current_request = self.requests[self.current_request_index]
		return self.current_request

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()

class Site:
    def __init__(self, name, switch, dtn):
        self.name = name
        self.switch = switch
        self.dtn = dtn

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()


class Config:
    def __init__ (self, switches=None,dtns=None,sites=None, data_subnet=None):
        if switches != None:
            self.switches = switches
        if dtns != None:
            self.dtns = dtns
        if sites != None:
            self.sites= sites
        self.data_subnet = data_subnet
    def save(self, config_file):
        f = open(config_file,"w")
        pickle.dump(obj=self,file=f)
        f.close()


def get_config(config_file):
	f = open(config_file)
	conf = pickle.load(f)
	f.close()
	for site in conf.sites:
		site.dtn.switch = site.switch

	return conf

class CoordRequest(scheduler.Request):

	def __init__ (self, src_dtn, dst_dtn, data_size, deadline, sched_req=None, description="",max_rate=0):
		scheduler.Request.__init__(self, src=src_dtn.name,dst=dst_dtn.name,size=data_size,ts=0,td=deadline)
		self.src_dtn = src_dtn
		self.dst_dtn = dst_dtn
		self.max_rate = max_rate
		self.received_datetime = datetime.datetime.now()
		self.deadline_datetime = self.received_datetime + datetime.timedelta(seconds=self.td)
		self.accepted = False
		self.start_time = None
		self.percent_completion = 0
		self.completed = False
		self.completed_ontime = False
		self.description = description
		self.coordinator = None

	def __str__(self):
		return  self.src_dtn.name + " -> " + self.dst_dtn.name + " completion: " + str(self.percent_completion) + " deadline: " + str(self.td)
	def __repr__(self):
		return self.__str__()


class Coordinator(threading.Thread):
	debug = False
	def __init__ (self, name, config_file, epoch_time, max_rate_mbps=500, scenario_file=None, algo='ljf',app_ip="localhost" ):
		threading.Thread.__init__(self)
		self.config_file = config_file
		self.scenario_file = scenario_file
		self.config = get_config(self.config_file)
		SingleFileGen.load(self.scenario_file, self.config.dtns)
		self.epoch_time = epoch_time
		self.accepted_requests = []
		self.rejected_request = []
		self.completed_requests = []
		self.current_requests = {}
		self.monitor_pending_requests = []
		self.lock = threading.Lock()
		self.isRunning = False
		self.algo = algo
		self.max_rate = max_rate_mbps * 1000 * 1000
		self.app_ip = app_ip
		self.scheduler = scheduler.Scheduler(epochx=self.epoch_time,algo=self.algo,max_rate=self.max_rate,debug=False)
		self.app = CoordApp(name="calibers-api", ip=self.app_ip, coord=self)

	def get_next_requests(self):
		new_requests = {}
		for dtn in self.config.dtns:
			if dtn.current_request != None and not dtn.current_request.completed:
				continue
			req = dtn.get_next_request()
			if req != None:
				new_requests[req.src_dtn.name] = req
		return new_requests

	def stop(self):
		self.isRunning = False

	def run(self):
		print "Coordinator is starting."
		self.isRunning = True
		while (self.isRunning):
			start_time = time.time()
			new_requests = self.get_next_requests()
			reqs = new_requests.values()
			if len(reqs) > 0:
				new_flows, rejected_flows, updated_flows = self.scheduler.sched(reqs)
				for flow in new_flows:
					req = new_requests[flow[0]]
					self.start_flow(req)
				for flow in updated_flows:
					req = new_requests[flow[0]]
					self.update_flow(req)
				for flow in rejected_flows:
					req = new_requests[flow[0]]
					self.reject_flow(req)
			end_time = time.time()
			time_to_sleep = 1.0 - (end_time - start_time)
			if (time_to_sleep < 0):
				print "Cannot keep up with processing an epoch"
			else:
				time.sleep (time_to_sleep)
		print "Request simulation is stopped."

	def start_flow(self, req):
		if Coordinator.debug:
			print "Start flow from",req
		with self.lock:
			self.current_requests[req.src_dtn.name] = req
			self.monitor_pending_requests.append(req)
		self.start_flow_dtn (req)

	def update_flow(self, req):
		pass

	def reject_flow(self, req):
		pass

	def start_flow_dtn(self, req):
		url = "http://" + req.src_dtn.ip + ":5000/" + str(req.size) + '-' + req.dst_dtn.ip + '-' + req.src_dtn.name
		try:
			#results = requests.put(url, params={'dest': req.dst_dtn.ip + ':9002/data/' + req.src_dtn.name})
			results = requests.put(url)
		except requests.exceptions.RequestException:
			return None
		if results.status_code==200:
			return results.text
		else: 
			return None

	def meters_port(self, req, rate):
		switch = req.src_dtn.switch
		switch.set_rate(rate)



class SingleFileGen:
	def __init__(self,sources,C,epoch,buckets,padding=1.2):
		self.capacity = C
		self.epoch = epoch
		self.sources = sources
		self.buckets=buckets
		self.padding = padding
		np.random.seed(3)

	def generate_requests(self,dst_dtn, iterations=1,scale = 0.1,min_bias=0.1):
		all_requests = []
		for iter in range(iterations):
			reqs = []
			for dtn in self.sources:
				size = np.random.choice(self.buckets)
				min_duration = (size * 8.0 * self.padding) / self.capacity 
				duration = min_duration * (np.random.exponential(scale=scale) + min_bias) + min_duration
				dst = 0
				req = CoordRequest(src_dtn=dtn,dst_dtn=dst_dtn,data_size=size,deadline=duration)
				req.min_duration = min_duration
				req.delay_ratio = ((req.td - req.min_duration) / req.min_duration) * 100
				reqs.append(req)
				dtn.requests.append(req)
			all_requests.append(reqs)
			if iterations == 1:
				return reqs
		return all_requests

	@staticmethod
	def save(file_name, reqs):
		f = open (file_name,"w")
		pickle.dump(reqs, f)
		f.close()

	@staticmethod
	def load(file_name, dtns):
		f = open (file_name)
		reqs =  pickle.load(f)
		f.close()
		reqs_per_dtn = zip(*reqs)
		dtn_index = 0
		for dtn in dtns:
			dtn.requests = list(reqs_per_dtn[dtn_index])
			dtn_index += 1
		return reqs

class GetConfig(Resource):
	__name__ = "GetConfig"
	app = None

	def __init__(self, app=None):
		if app != None:
			GetConfig.app = app

	def get(self):
		if GetConfig.app == None:
			return "error"
		res = {}
		sites={}
		res['sites'] = sites
		for site in GetConfig.app.coord.config.sites:
			sites[site.name] = {'dtn':site.dtn.name, 'rtt':site.switch.rtt}
		return res



class NewTransfers(Resource):
	__name__ = "NewTransfers"
	app = None

	def __init__(self, app=None):
		if app != None:
			NewTransfers.app = app

	def get(self):
		result = {}
		if NewTransfers.app == None:
			return []
		with self.app.coord.lock:
			for req in  NewTransfers.app.coord.monitor_pending_requests:
				entry = {}
				entry["file_route"] = "/tmp/files_storage/" + req.src_dtn.name
				entry["expected_size"] = req.size
				entry["deadline"] = time.time() + req.td
				result[req.src_dtn.name] = entry
			NewTransfers.app.coord.monitor_pending_requests = []	
		return result

class Shutdown(Resource):
	__name__ = "Shutdown"
	app = None

	def __init__(self, app=None):
		if app != None:
			Shutdown.app = app

	def post(self):
		func = request.environ.get('werkzeug.server.shutdown')
		if func is None:
			return 'Not running with the Werkzeug Server'
		func()
		return "Shutdown in progress..."


class FlowUpdate(Resource):
	__name__ = "FlowUpdate"
	app = None
	parser = None

	def __init__(self, app=None):
		if app != None:
			FlowUpdate.app = app
			FlowUpdate.parser = reqparse.RequestParser()
			FlowUpdate.parser.add_argument('timestamp', type=float, help='Timestamp seconds since epoch.')
			FlowUpdate.parser.add_argument('received', type=int, help='Received bytes.')
			FlowUpdate.parser.add_argument('completion', type=float, help='Receiving rate of the file.')
			FlowUpdate.parser.add_argument('rate', type=float, help='Receiving rate of the file.')

	def put(self, filename):
		args = FlowUpdate.parser.parse_args()
		return {'result': filename}

class CoordApp:
	def __init__(self, name,coord,ip='127.0.0.1'):
		self.ip = ip
		self.coord = coord
		self.app = Flask("__nae__")
		self.api = Api(self.app)
		self.set_endpoints()
		self.set_api()
		self.flaskRunThread = threading.Thread(target=self.run)
		self.flaskRunThread.start()

	def set_endpoints(self):
		self.app.add_url_rule('/api/','current',self.current)

	def set_api(self):
		self.api.add_resource(FlowUpdate(app=self), '/api/files/<filename>')
		self.api.add_resource(Shutdown(app=self), '/api/stop')
		self.api.add_resource(NewTransfers(app=self), '/api/configs/')
		self.api.add_resource(GetConfig(app=self), '/api/config/')


	def run(self):
		self.app.run(host=self.ip, threaded=True)

	def current(self):
		print "CURRENT"
		return "current requests"

	def update_flow (self, src, completion, rate):
		print "Update from",src,"completion",completion,"rate",rate








