from functools import partial, wraps
import simpy 


import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

import time

class WorkFlow:
	def __init__(self,topology,name):
		self.topology = topology
		self.name = name
		self.debug = False or self.topology.debug
		self.info = True or self.topology.debug

	def receive(self):
		return

	def start(self):
		return

	def failed(self, net_elem):
		return

	def reset(self):
		return

def increase_default(flow):
	rate = min (flow.current_rate + flow.increase_step, flow.max_rate)
	if rate != flow.current_rate:
		flow.current_rate = rate
		return True
	return False

def decrease_default(flow):
	rate = max (flow.current_rate / 2, flow.increase_step)
	if rate != flow.current_rate:
		flow.current_rate = rate
		return True
	return False

class DataTransfer(WorkFlow):
	def __init__(self,name,src,dst,topology,data_size,max_rate,path=None,increase=None,decrease=None,debug=None,):
		WorkFlow.__init__(self,topology=topology, name=name)
		if debug != None:
			self.debug = debug
		else:
			self.debug = topology.debug
		self.env = self.topology.env
		self.path = path
		self.data_size = data_size
		self.max_rate = max_rate
		self.increase = increase
		self.src = src
		self.dst = dst	
		if self.increase == None:
			self.increase = increase_default
		self.decrease = decrease
		if self.decrease == None:
			self.decrease = decrease_default	
		if path == None:
			src_port = self.src.all_ports.values()[0]
			dst_port = self.dst.all_ports.values()[0]
			g = self.topology.get_graph()
			path = nx.shortest_path(g, src_port, dst_port)
			self.graph = g
		self.path = path
		self.rtt = self.topology.rtt(self.path)
		self.reset()
		self.record_receive = False
		self.record_drop = False 

	def reset(self):
		self.received = 0
		self.completed = False
		self.increase_step = np.ceil(float(self.max_rate) *  0.01)
		self.current_rate = self.increase_step
		self.start_time = self.topology.now()
		self.end_time = 0
		self.receive_data = []
		self.drop_data = []
		self.congested = False	
		self.forward_map = self.compute_map()
		self.last_receive_update = self.topology.now()
		self.flowrates = []
		self.receive_rate = 0

	def compute_map(self,path=None):
		forward_map = {}
		if path == None:
			path = self.path
		for port in path:
			if self.topology.is_last_port(current_port=port, path=path):
				forward_map[port.name] = None
			else:
				forward_map[port.name] = self.topology.next_port(current_port=port, path=path)
		return forward_map	
					

	def computes_stats(self):
			current_time = self.end_time
			if not self.completed:
				current_time = self.topology.now()
			self.elapse_time = (current_time - self.start_time) / 1000
			self.average = self.data_size / self.elapse_time		

	def flowrate_change(self, flowrate):
		if self.debug or self.topology.debug: print self.topology.now(),"flow:",self.name,"rate change from:",self.receive_rate,"to:",flowrate.rate
		self.update_stats()
		self.receive_rate = flowrate.rate

	def compute_map(self,path=None):
		forward_map = {}
		if path == None:
			path = self.path
		for port in path:
			if self.topology.is_last_port(current_port=port, path=path):
				forward_map[port.name] = None
			else:
				forward_map[port.name] = self.topology.next_port(current_port=port, path=path)
		return forward_map	

	def update_stats(self):
		now = self.topology.now()
		elapsed = now - self.last_receive_update
		update = int(float(self.receive_rate/1000) * elapsed)
		self.received += update
		self.last_receive_update = now
		#if self.debug or self.topology.debug: print self.topology.now(),"flow:",self.name,"receive update", update
		if self.record_receive: self.receive_data.append([float(now)/1000,self.receive_rate])

	def start(self):
		self.reset()
		if self.record_drop:
			for port in self.path:
				port.record_drop = True
		if self.info: print self.topology.now(),"start file transfer",self.name
		port_in = self.path[0]	
		while self.received <= self.data_size:	
			self.update_stats()
			if self.debug or self.topology.debug: print self.topology.now(),"flow:",self.name,"received:",self.received,"sending rate",self.current_rate,"congested",self.congested
			if self.congested:
				if self.decrease(flow=self):
					flowrate = FlowRate(flow=self,rate = self.current_rate)
					port_in.router.flowrate_change(flowrate=flowrate, port_in=port_in)
			if not self.congested:
				if self.increase(flow=self):
					flowrate = FlowRate(flow=self,rate = self.current_rate)
					port_in.router.flowrate_change(flowrate=flowrate, port_in=port_in)
			yield self.topology.timeout(self.rtt)

		flowrate = FlowRate(flow=self,rate = 0)	
		port_in.router.flowrate_change(flowrate=flowrate, port_in=port_in)	 
		self.completed = True
		self.end_time = self.topology.now()
		self.computes_stats()
		if self.info: print "time:",self.elapse_time,'secs',self.name,'rtt:', self.rtt,'average',self.average
		self.cleanup_path()

	def cleanup_path(self):
		for port in self.path:
			if self.name in port.flowrates:
				del port.flowrates[self.name]

	def plot_receive(self):
		x,y = zip(*self.receive_data)
		plt.plot(x,y,label=self.name)
		plt.plot(x,y)
		plt.xlabel('milliseconds')
		plt.ylabel('Mbps')

	def plot_drop(self):
		x,y = zip(*self.drop_data)
		plt.plot(x,y,label=self.name + "drop")
		plt.xlabel('milliseconds')
		plt.ylabel('Nb of drops')

	def plot_path_drop(self):
		for port in self.path:
			x,y = zip(*port.drops)
			plt.plot(x,y,label=port.name)
			plt.xlabel('seconds')
			plt.ylabel('dropped throughput')

class FlowRate:
	def __init__(self, flow, rate=0):
		self.flow = flow
		self.rate = rate

	def __str__(self):
		return self.flow.name+':'+str(self.rate)
	def __repr__(self):
		return self.__str__()

class Router:
	def __init__(self,name,topology=None,capacity=None):
		self.topology = topology
		self.env = topology.env
		self.name = name
		self.all_ports = {}
		self.fabric_links = {}
		self.topology = topology
		self.capacity=capacity
		self.info = True or self.topology.debug
		self.debug = False or self.topology.debug

	def flowrate_change(self, port_in, flowrate):
		if self.debug or self.topology.debug: print self.topology.now(),"router:",self.name,"flow:",flowrate.flow.name,"port_in:",port_in,"rate change to:",flowrate.rate
		next_port = flowrate.flow.forward_map[port_in.name]
		if next_port == None:
			flowrate.flow.flowrate_change(flowrate=flowrate)
			return
		if not next_port.name in port_in.links_out:
			print "invalid path"
			return
		link = port_in.links_out[next_port.name]
		link.flowrate_change(flowrate=flowrate)	

	def add_port(self,port=None,name=None,capacity=None):
		if port == None:
			if capacity == None:
				if self.capacity == None:
					print "either the router or the port must have a capacity set to something else than None"
					return None
				capacity = self.capacity
			port_nb = str(len(self.all_ports) + 1)
			if name == None:
				name =port_nb
			else:
				name = name + ":" + port_nb
			port = Port(name=name,topology=self.topology,capacity=capacity)
			port.router = self
		self.all_ports[port.name] = port
		for p in self.all_ports.values():
			if p == port:
				continue
			link_name_a_b = self.name + ":" + port.name + "->" + self.name + ":" + p.name
			if not link_name_a_b in self.fabric_links:
				link = Link(name=link_name_a_b,latency=0,topology=self.topology)
				self.fabric_links[link.name] = name
				port.links_out[p.name] = link
				p.links_in[port.name] = link
				link.port_in = port
				link.port_out = p
				self.topology.all_links[link.name] = link

			link_name_b_a = self.name + ":" + p.name + "->" + self.name + ":" + port.name
			if not link_name_b_a in self.fabric_links:
				link = Link(name=link_name_b_a,latency=0,topology=self.topology)
				self.fabric_links[link.name] = name
				p.links_out[port.name] = link
				port.links_in[p.name] = link
				link.port_in = p
				link.port_out = port
				self.topology.all_links[link.name] = link

		return port

	def __str__(self):
		return self.name
	def __repr__(self):
		return self.__str__()

class Port:
	def __init__ (self,name,topology,capacity):
		self.topology = topology
		self.env = topology.env
		self.name = name
		self.links_in = {}
		self.links_out = {}		
		self.capacity = capacity
		self.router = None
		self.topology.all_ports[self.name] = self
		self.flowrates = {}
		self.info = True or self.topology.debug
		self.debug = False or self.topology.debug
		self.record_drop = True
		self.drops = []
		self.debug = False
		self.congested = False

	def total_flowrates(self):
		total = 0
		for flowrate in self.flowrates.values():
			if flowrate.flow.completed:
				#left over. ignore
				if flowrate.flow.name in self.flowrates:
					del self.flowrates[flowrate.flow.name]
				continue
			total += flowrate.rate
		return total

	def flowrate_change(self, flowrate):
		flow = flowrate.flow
		if flowrate.flow.completed or flowrate.rate == 0:
			#left over. ignore
			if flowrate.flow.name in self.flowrates:
				del self.flowrates[flowrate.flow.name]
		else:
			self.flowrates[flow.name] = flowrate
			if self.debug or self.topology.debug:
				print self.topology.now(),"port:",self.name,"total rate",flow.current_rate,"flow:",flowrate.flow.name,"change rate to",flowrate.rate
		if self.total_flowrates() > self.capacity:
			self.congested = True
			#print "port",self.name,"is congested",self.total_flowrates()
			for rate in self.flowrates.values():
				rate.flow.congested = True
		else:
			if self.congested:
				self.congested = False
				#print "port",self.name,"is no longer congested",self.total_flowrates()
				for rate in self.flowrates.values():
					rate.flow.congested = False

		self.router.flowrate_change(flowrate=flowrate,port_in=self)			

	def __str__(self):
		return self.name
	def __repr__(self):
		return self.__str__()
		
class Link:
	def __init__(self,name, topology, latency=0):
		self.name = name
		self.topology = topology
		self.env = topology.env
		self.latency = latency
		if self.env != None:
			pass
			#self.receive = self.env.process(self.receive())
		self.port_in = None
		self.port_out = None
		self.info = True or self.topology.debug
		self.debug = False or self.topology.debug

	def do_latency(self, flowrate):
		yield self.topology.timeout(self.latency)
		self.receive_flowrate_change(flowrate)

	def flowrate_change(self, flowrate): 
		if self.debug or self.topology.debug: print self.topology.now(),"link:",self.name,"flow:",flowrate.flow.name,"change ate to:",flowrate.rate
		if (self.latency > 0):
			self.env.process(self.do_latency(flowrate))
		else:
			self.receive_flowrate_change(flowrate)
	
	def receive_flowrate_change(self, flowrate):
		if self.debug or self.topology.debug: print self.topology.now(),"link:",self.name,"flow:",flowrate.flow.name,"received rate change:",flowrate.rate
		if self.port_in == None or self.port_in.router == None:
			print "path error"
			return
		self.port_out.flowrate_change(flowrate=flowrate)

	def __str__(self):
		return self.name
			

class Endpoint(Router):
	def __init__(self,name,topology,capacity,rate=0):
		Router.__init__(self,name=name,capacity=capacity,topology=topology)
		self.rate = rate
		self.topology.all_routers[self.name] = self
		self.info = True or self.topology.debug
		self.debug = False or self.topology.debug

	def connect(self,router,latency=0):
		if isinstance(router, basestring):
			if router in self.topology.all_routers:
				router = self.topology.all_routers[router]
			else:
				router = Router(name=router,capacity=capacity,topology=self.topology)
				self.topology.all_routers[router.name] = router
		self.topology.add_link(self, router, capacity=self.capacity, latency=latency)
	def __str__(self):
		return self.name

class Topology:
	def __init__(self,name="Unknown",env=None,ticks_per_sec=100):
		self.name = name
		self.all_routers = {}
		self.all_ports = {}
		self.all_links = {} 
		self.tick_millis = round(1000 / ticks_per_sec)
		self.ticks_per_sec = ticks_per_sec
		self.env = env
		if self.env == None:
			 self.env = simpy.Environment()
		self.workflows = {}
		self.info = True
		self.debug = False

	def get_router(self,name):
		if name in self.routers:
			return self.routers[name]
		else:
			return None

	def add_routers(self,routers):
		for router in routers:
			self.add_router(router = router)

	def add_links(self, links):
		for router_a, router_b, capacity, latency in links:
			r_a = self.get_router(router_a)
			if r_a == None:
				print router_a, "does not exist"
				return None
			r_b = self.get_router(router_b)
			if r_b == None:
				print router_b, "does not exist"
				return None	
			self.add_link(router_a=r_a, router_b=r_b, capacity=capacity, latency=latency)

	def rtt(self, path):
		latency = 0
		for port in path:
			if self.is_last_port(current_port=port, path=path):
				break
			next_port = self.next_port(current_port=port, path=path)
			link = port.links_out[next_port.name]
			latency += link.latency
		return latency * 2

	def next_port(self, current_port, path):
		if not current_port in path:
			return None
		next_port = path[path.index(current_port) + 1]
		return next_port			

	def is_last_port(self, current_port, path):
		return path[-1] == current_port

	def add_router(self, router):
		if isinstance(router,basestring) and not router in self.all_routers:
				router = Router(name=router, topology=self)
		else:
				router = self.all_routers[router]
		router.topology = self
		self.all_routers[router.name] = router

	def add_link(self, router_a, router_b, capacity, latency):
		if isinstance(router_a,basestring):
			if router_a in self.all_routers:
				router_a = self.all_routers[router_a]
			else:
				router = Router(name=router_a,capacity=capacity,topology=self)
				self.all_routers[router_a] = router
				router_a = router
		else:
			if not router_a.name in self.all_routers:
				self.all_routers[router_a.name] = router_a

		if isinstance(router_b,basestring):
			if router_b in self.all_routers:
				router_b = self.all_routers[router_b]
			else:
				router = Router(name=router_b,capacity=capacity,topology=self)
				self.all_routers[router_b] = router
				router_b = router
		else:
			if not router_b.name in self.all_routers:
				self.all_routers[router_b.name] = router_b 

		port_a = router_a.add_port(name=router_a.name + "->" + router_b.name,capacity=capacity)
		port_b = router_b.add_port(name=router_b.name + "->" + router_b.name,capacity=capacity)

		link_a_b = Link(name = router_a.name+":"+port_a.name+"->"+router_b.name+":"+router_b.name, latency=latency, topology=self)
		link_b_a = Link(name = router_b.name+":"+router_b.name+"->"+router_a.name+":"+port_a.name, latency=latency, topology=self)
		port_a.links_out[port_b.name] = link_a_b
		port_b.links_in[port_a.name] = link_a_b
		link_a_b.port_in = port_a
		link_a_b.port_out = port_b
		port_b.links_out[port_a.name] = link_b_a
		port_a.links_in[port_b.name] = link_b_a
		link_b_a.port_in = port_b
		link_b_a.port_out = port_a

		self.all_links[link_a_b.name] = link_a_b
		self.all_links[link_b_a.name] = link_b_a


	def timeout_until_next_sec(self):
		now = self.env.now * self.tick_millis
		remain = (now/1000 + 1) * 1000 - now
		return self.timeout(remain)

	def timeout(self,millisecs):
		if millisecs < self.tick_millis:
			print "Cannot create timeout of ",millisecs," because tick time is too long:", self.tick_millis
			return self.env.timeout(self.tick_millis)
		return self.env.timeout(millisecs/self.tick_millis)

	def now(self):
		return self.env.now * self.tick_millis

	def sim_rate(self):
		real_time_stop = time.time()
		simulated_time_stop = self.now()
		real_time_elapse = real_time_stop - self.real_time_start
		simulated_elapse = simulated_time_stop - self.simulated_time_start
		return simulated_elapse, real_time_elapse,float(simulated_elapse)/(real_time_elapse*1000)

	def start_simulation(self, until_sec=0, until_millis=0):
		duration = 0
		if until_millis > 0:
			duration = until_millis
		if until_sec > 0:
			duration = until_sec * 1000
		duration = np.ceil(duration / self.tick_millis)
		self.real_time_start = time.time()
		self.simulated_time_start = self.now()
		print "Simulation starts",self.now()
		if duration > 0:
			self.env.run(until=self.env.now + duration)
		else:
			self.env.run()
		simulated_elapse,real_time_elapse,rate = self.sim_rate()
		print "Simulation stopped simulated elapse time:", simulated_elapse/1000,"real time:", real_time_elapse,"real/simulate:",rate


	def schedule_workflow(self, workflow, when_sec=0, when_millis=0,delay_sec=0, delay_millis=0):
		timeout = None
		if when_sec > 0:
			when_millis = when_sec * 1000
		if when_millis > 0:
			if when_millis < self.now():
				print "Cannot schedule workflow in the past"
				return
			delay_millis = self.when_millis - self.now()
		else:
			if delay_sec > 0:
				delay_millis = delay_sec * 1000
		if delay_millis > 0:
			timeout = self.timeout(delay_millis)
		p = self.env.process(workflow.start())
		workflow.main_process = p
		self.workflows[workflow.name] = workflow

	def get_graph(self):
		graph = nx.Graph()
		for link in self.all_links.values():
				port_a = link.port_in
				port_b = link.port_out
				graph.add_edge(port_a,port_b)
		return graph

	def draw(self):
		graph = self.get_graph()
		pos=nx.spring_layout(graph)
		nx.draw_networkx_edges(graph,pos)
		nx.draw_networkx_nodes(graph,pos,node_size=100,alpha=0.5,color='b')
		nx.draw_networkx_labels(graph,pos,font_size=8,font_family='sans-serif')
		plt.axis('off')
		plt.show()

	def show_plots(self):
		plt.legend()
		plt.show()



