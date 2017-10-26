import pickle
import threading
from datetime import datetime

class Switch:
    def __init__(self, name, ip, port, vfc, ofport, rtt, cert_file=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.vfc = vfc
        self.ofport = ofport
        self.rtt = rtt
        self.cert_file = cert_file
        if self.cert_file != None:
        	f = open(self.cert_file)
        	self.cert = f.read()
        	f.close()
        else:
        	self.cert - None

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()
       

class Container:
    def __init__(self, name, ip, port, bias_fun=None, bias_args=None):
        self.name = name
        self.ip = ip
        self.port = port
        self.bias_fun = bias_fun
        self.bias_args = bias_args

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()

class Site:
    def __init__(self, name, switch, container):
        self.name = name
        self.switch = switch
        self.container = container

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()


class Config:
    def __init__ (self, switches=None,containers=None,sites=None):
        if switches != None:
            self.switches = switches
        if containers != None:
            self.containers = containers
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

class Request:
	def __init__ (self, src_dtn, dst_dtn, data_size, max_rate, deadline_datetime, description=""):
		self.src_dtn = src_dtn
		self.dst_dtn = dst_dtn
		self.max_rate = max_rate
		self.deadline = deadline
		self.received_datetime = datetime.now()
		self.deadline_datetime = deadline_datetime
		self.accepted = False
		self.start_time = None
		self.percent_completion = 0
		self.completed = False
		self.completed_ontime = False
		self.description = description
		self.coordinator = None

		def accepted(self):
			pass

		def rejected(self):
			pass

		def completed(self):
			pass

		def started(self):
			pass
		def updated(self):
			pass

	def __str__(self):
		return self.description + ": " + self.src_dtn + " -> " + self.dst_dtn + " completion: " + self.percent_completion
	def __repr__(self):
		return self.__str__()


class Coordinator:
	def __init__ (self, name, config_file, epoch_time, ):
		self.config_file = config_file
		self.epoch_time = epoch_time
		self.accepted_requests = []
		self.rejected_request = []
		self.completed_requests = []
		self.pending_requests = []
		self.lock = threading.Lock()

	def request_transfer (self, request):
		request.coordinator = self
		with self.lock:
			self.pending_requests.append(request)

	def request_completed (self, request):
		pass








