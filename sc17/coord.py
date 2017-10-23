import pickle

class Switch:
    def __init__(self, name, ip, port, vfc, ofport, rtt):
        self.name = name
        self.ip = ip
        self.port = port
        self.vfc = vfc
        self.ofport = ofport
        self.rtt = rtt

    def __str__(self):
    	return self.name
    def __repr__(self):
    	return self.__str__()
       

class Container:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port

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
        