from functools import partial, wraps
import simpy

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

def trace(env, callback):
	def get_wrapper(env_step, callback):
		@wraps(env_step)
		def tracing_step():
			if len(env._queue):
				t, prio, eid, event = env._queue[0]
				callback(t, prio, eid, event)
			return env_step()
		return tracing_step
	env.step = get_wrapper(env.step, callback)

def monitor(data, t, prio, eid, event):
	data.append((t, eid, type(event)))

class WorkFlow:
	def __init__(self,topology,name):
		self.topology = topology
		self.name = name
		self.debug = False
		self.info = True

	def receive(self,packet):
		return

	def start(self):
		return

	def failed(self, packet,net_elem):
		return


class DataTransfer(WorkFlow):
	def __init__(self,name,src,dst,topology,data_size,max_rate,path=None,increase=None,decrease=None):
		WorkFlow.__init__(self,topology=topology, name=name)
		self.env = self.topology.env
		self.data_size = data_size
		self.received = 0
		self.path = path
		self.max_rate = max_rate
		self.packet_drop = 0
		self.packet_total = 0
		self.completed = False
		self.increase = increase
		self.increase_step = int(np.ceil(float(self.max_rate) *  0.1 / self.topology.ticks_per_sec))
		self.current_rate = self.increase_step
		self.start_time = self.env.now
		self.end_time = 0
		self.receive_data = []
		self.drop_data = []
		self.src = src
		self.dst = dst
		if self.increase == None:
			self.increase = self.increase_default
		self.decrease = decrease
		if self.decrease == None:
			self.decrease = self.decrease_default		
		if self.path == None:
			src_port = self.src.all_ports.values()[0]
			dst_port = self.dst.all_ports.values()[0]
			g = self.topology.get_graph()
			self.path = nx.shortest_path(g, src_port, dst_port)

	def increase_default(self):
		self.current_rate = min (self.current_rate + self.increase_step, self.max_rate)

	def decrease_default(self):
		self.current_rate = max (self.current_rate / 2, self.increase_step)

	def receive(self,packet):
		if self.completed:
			return
		self.received += packet.size
		if self.debug: print self.env.now,self.name,"packet received",packet.name,packet.size,self.received
		self.receive_data.append([self.topology.env.now,packet.size])
		self.increase()
		if (self.received >= self.data_size):
			p = 100
			if self.packet_total != 0:
				p = self.packet_drop*100/self.packet_total
			self.completed = True
			self.end_time = self.env.now
			duration = self.start_time - self.end_time
			if self.info: print self.env.now,self.name,'success',self.received,'packets',self.packet_total,'drop',self.packet_drop,' ',p,'%'

	def start(self):
		#import pdb; pdb.set_trace()
		if self.info: print self.env.now,"start file transfer",self.name

		max_rate_per_tick = int(np.ceil(float(self.max_rate) / self.topology.ticks_per_sec))

		while not self.completed:
			rate_per_tick = int(np.ceil(float(self.current_rate) / self.topology.ticks_per_sec))
			packet_size = min(rate_per_tick,self.data_size - self.received, max_rate_per_tick)
			packet_name = self.name+"-"+str(self.packet_total + 1)
			packet = Packet(topology=self.topology, size=packet_size,flow=self,name=packet_name,path=self.path)
			port_in = self.path[0]
			port_in.router.forward(packet=packet, port_in=port_in)	
			self.packet_total += 1
			yield self.topology.env.timeout(1)


	def failed(self, packet,net_elem):
		if self.completed:
			return
		if net_elem != None:
			if self.debug: print self.env.now,self.name,"drop packet ",packet.name ,"at",net_elem.name
		else:
			if self.debug: print self.env.now,self.name,"drop packet ",packet.name ,'broken link'
		self.drop_data.append([self.topology.now(),packet.size])
		self.packet_drop += 1
		self.decrease()

	def plot_receive(self):
		tick_now = int (self.topology.env.now)
		y = np.full((tick_now),0, dtype=int)
		for v in self.receive_data:
			y[int(v[0])] = v[1]
		x = range(tick_now)
		plt.plot(x,y,label=self.name + "throughput")
		plt.xlabel('milliseconds')
		plt.ylabel('Mb')

	def plot_drop(self):
		x,y = zip(*self.drop_data)
		plt.plot(x,y,label=self.name + "drop")
		#plt.plot(self.throughput_data,self.drop_data)
		plt.xlabel('milliseconds')
		plt.ylabel('Mb')


class Packet:
	def __init__ (self,topology,name,size,flow,path=[]):
		self.topology = topology
		self.env = topology.env
		self.name = name
		self.size = size
		self.path = path
		self.flow = flow
		self.hop = 0

	def next_port(self, current_port):
		if not current_port in self.path:
			return None
		next_port = self.path[self.path.index(current_port) + 1]
		return next_port			

	def is_last_port(self, current_port):
		return self.path[-1] == current_port

	def receive(self):
		self.flow.receive(self)

	def failed(self,net_elem):
		if self.flow != None:
			self.flow.failed(packet=self,net_elem=net_elem)

	def __str__(self):
		return self.name
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

	def forward(self, port_in, packet):
		if packet.is_last_port(current_port=port_in):
			packet.receive()
			return
		next_port = packet.next_port(current_port = port_in)
		if next_port != None:
			if not next_port.name in port_in.links_out:
				packet.failed(net_elem=port_in)
				return
			link = port_in.links_out[next_port.name]
			port_in.send(packet=packet, link_out=link)
		else:
			packet.failed(net_elem=port_in)

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
				link = Link(name=link_name_a_b,capacity=min(port.capacity,p.capacity),latency=0,topology=self.topology)
				self.fabric_links[link.name] = name
				port.links_out[p.name] = link
				p.links_in[port.name] = link
				link.port_in = port
				link.port_out = p
				self.topology.all_links[link.name] = link

			link_name_b_a = self.name + ":" + p.name + "->" + self.name + ":" + port.name
			if not link_name_b_a in self.fabric_links:
				link = Link(name=link_name_b_a,capacity=min(port.capacity,p.capacity),latency=0,topology=self.topology)
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
		self.capacity_per_tick = np.round(self.capacity / self.topology.ticks_per_sec)
		self.router = None
		self.topology.all_ports[self.name] = self
		self.in_flight = 0
		self.last_period = 0
		self.packets_out = []

	def send(self,packet,link_out):
		if self.last_period != self.topology.env.now:
			self.in_flight = 0
			self.last_period = self.topology.env.now
			for p,l in self.packets_out:
				l.put(p)
			self.packets_out = []
		self.packets_out.append((packet, link_out))
		self.in_flight += packet.size
		while self.capacity_per_tick < self.in_flight:
			p = self.packets_out[np.random.randint(0, len(self.packets_out))]
			self.packets_out.remove(p)
			self.in_flight -= p[0].size
			p[0].failed(net_elem=self)

	def __str__(self):
		return self.name
	def __repr__(self):
		return self.__str__()
		
class Link:
	def __init__(self,name, topology, latency=0, capacity=0):
		self.name = name
		self.topology = topology
		self.env = topology.env
		self.latency = latency
		self.capacity = 0
		if self.capacity != 0:
			self.store = simpy.Store(self.env, capacity=self.capacity)
		else:
			self.store = simpy.Store(self.env)
		if self.env != None:
			self.receive = self.env.process(self.receive())
		self.port_in = None
		self.port_out = None

	def latency(self, packet):
		yield self.topology.timeout(self.latency)
		self.store.put(packet)

	def put(self, packet): 
		if (self.latency > 0):
			self.env.process(self.latency(packet))
		else:
			self.store.put(packet)
	
	def receive(self):
		while True: 
			packet = yield self.store.get()
			if self.port_in == None or self.port_in.router == None:
				packet.failed(net_elem=self)
				return
			self.port_out.router.forward(packet=packet, port_in=self.port_out)

	def __str__(self):
		return self.name
			

class Endpoint(Router):
	def __init__(self,name,topology,capacity,rate=0):
		Router.__init__(self,name=name,capacity=capacity,topology=topology)
		self.rate = rate
		self.topology.all_routers[self.name] = self

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
		self.tick_millis = np.round(1000 / ticks_per_sec)
		self.ticks_per_sec = ticks_per_sec
		self.env = env
		if self.env == None:
			 self.env = simpy.Environment()

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

	def add_router(self, router):
		if isinstance(router,basestring) and not router in self.all_routers:
				router = Router(name=router, topology=self)
		else:
				rooter = self.all_routers[rooter]
		router.topology = self
		self.all_routers[router.name] = router


	def add_link(self, router_a, router_b, capacity, latency):
		if isinstance(router_a,basestring):
			if router_a in self.all_routers:
				router_a = self.all_routers[router_a]
			else:
				router = Router(name=router_a,capacity=capacity,topology=self)
				self.all_routers[router_a] = router
				router_a = rooter
		else:
			if not router_a.name in self.all_routers:
				self.all_routers[router_a.name] = router_a

		if isinstance(router_b,basestring):
			if router_b in self.all_routers:
				router_b = self.all_routers[router_b]
			else:
				router = Router(name=router_b,capacity=capacity,topology=self)
				self.all_routers[router_b] = router
				router_b = rooter
		else:
			if not router_b.name in self.all_routers:
				self.all_routers[router_b.name] = router_b 

		port_a = router_a.add_port(name=router_a.name + "->" + router_b.name,capacity=capacity)
		port_b = router_b.add_port(name=router_b.name + "->" + router_b.name,capacity=capacity)

		link_a_b = Link(name = router_a.name+":"+port_a.name+"->"+router_b.name+":"+router_b.name, latency=latency, capacity=capacity,topology=self)
		link_b_a = Link(name = router_b.name+":"+router_b.name+"->"+router_a.name+":"+port_a.name, latency=latency, capacity=capacity,topology=self)
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

	def start_simulation(self, until_sec=0, until_millis=0):
		duration = 0
		if until_millis > 0:
			duration = until_millis
		if until_sec > 0:
			duration = until_sec * 1000
		duration = np.ceil(duration / self.tick_millis)
		print "Simulation starts at ",self.env.now, "and will run until ", self.env.now + duration
		if duration > 0:
			self.env.run(until=self.env.now + duration)
		else:
			self.env.run()
		print "Simulation stops at",self.env.now

	def stop_simulation(self):
		self.env.run(until=self.env.now +1)

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
		#if timeout != None:
		#	yield timeout
		p = self.env.process(workflow.start())
		workflow.main_process = p

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



