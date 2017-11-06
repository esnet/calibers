import pickle
import threading
import time
import datetime
import numpy as np
from flask import Flask
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
    def __init__ (self, switches=None,dtns=None,sites=None):
        if switches != None:
            self.switches = switches
        if dtns != None:
            self.dtns = dtns
        if sites != None:
            self.sites= sites
    def save(self, config_file):
        f = open(config_file,"w")
        pickle.dump(obj=self,file=f)
        f.close()


def get_config(config_file):
	f = open(config_file)
	conf = pickle.load(f)
	f.close()
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
		return  self.src_dtn.name + " -> " + self.dst_dtn.name + " completion: " + str(self.percent_completion)
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
		self.current_requests = []
		self.lock = threading.Lock()
		self.isRunning = False
		self.algo = algo
		self.max_rate = max_rate_mbps * 1000 * 1000
		self.app_ip = app_ip
		self.scheduler = scheduler.Scheduler(epoch=self.epoch_time,algo=self.algo,max_rate=self.max_rate,debug=False)
		self.app = CoordApp(name="calibers-api", ip=self.app_ip, coord=self)

	def get_next_requests(self):
		new_requests = []
		for dtn in self.config.dtns:
			if dtn.current_request != None and not dtn.current_request.completed:
				continue
			req = dtn.get_next_request()
			if req != None:
				new_requests.append(req)
		return new_requests

	def stop(self):
		self.isRunning = False

	def run(self):
		self.isRunning = True
		while (self.isRunning):
			start_time = time.time()
			new_requests = self.get_next_requests()
			if len(new_requests) > 0:
				new_flows, rejected_flows, updated_flows = self.scheduler.sched(new_requests)
				if Coordinator.debug:
					print new_flows, rejected_flows, updated_flows
					tr = 0
					for f in new_flows:
						tr += f[1]
						print "total", tr/1000/1000
			end_time = time.time()
			time_to_sleep = 1.0 - (end_time - start_time)
			if (time_to_sleep < 0):
				print "Cannot keep up with processing an epoch"
			else:
				time.sleep (time_to_sleep)
		print "Request simulation is stopped."

	def process_flows (self, new_flows, updated_flows, rejected_flows):

		for flow in new_flows:
			self.start_flow(flow)
		for flow in updated_flows:
			self.update_flow(flow)
		for flow in rejected_flows:
			self.reject_flow(flow)

	def start_flow(self, flow):
		self.current_requests.append(flow)

	def update_flow(self, flow):
		pass

	def reject_flow(self, flow):
		pass


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
			requests = []
			for dtn in self.sources:
				size = np.random.choice(self.buckets)
				min_duration = (size * 8 * 1000 * self.padding) / self.capacity 
				duration = min_duration * (np.random.exponential(scale=scale) + min_bias) + min_duration
				dst = 0
				req = CoordRequest(src_dtn=dtn,dst_dtn=dst_dtn,data_size=size,deadline=duration)
				req.min_duration = min_duration
				req.delay_ratio = ((req.td - req.min_duration) / req.min_duration) * 100
				requests.append(req)
				dtn.requests.append(req)
			all_requests.append(requests)
			if iterations == 1:
				return requests
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

class ReceivedFile:

	src_root_path = "/storage"
	dst_root_path = "/storage"

	def __init__ (self,name,size,src_dtn):
		self.name = name
		self.size = size
		self.src_dtn = src_dtn
		self.received = 0
		self.completion = 0.0
		self.last_received = 0.0
		self.last_timestamp = 0.0
		self.id = self.dtn.name + name + "-" + str(self.size)
		self.comment = self.id


class NewTransfers(Resource):
	__name__ = "NewTransfers"
	last_polled = []
	app = None

	def __init__(self, app=None):
		if app != None:
			FlowUpdate.app = app

	def get(self):
		new_requests = []
		if NewTransfers.app == None:
			return []
		for req in  NewTransfers.app.coord.current_requests:
			pass


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
		print "TEST", args == None
		print "ARGS", args
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
		self.app.add_url_rule('/','current',self.current)

	def set_api(self):
		self.api.add_resource(FlowUpdate(app=self), '/api/files/<filename>')



	def run(self):
		self.app.run(host=self.ip, threaded=True)

	def current(self):
		return "current requests"

	def update_flow (self, src, completion, rate):
		print "Update from",src,"completion",completion,"rate",rate








