# new flow: in pace, for each link sort flows by SJF or LJF, then take salck value(s) and assign it ot he new flow until it get Rmin 
# completed flow(s): in reshape, for all completed flows, find all involved links, then find all involved flows, then sor involved flows based on SJF or LJF, and distribute Rresid accordingly

import time
import random
from math import *
import numpy as np
from coord import BaseRequest

epoch = 100.0 #300.0 #1 #timeslot, periodic sceduling, unit seconds
C = int(10000 * 1e6) #link capaacity in bps

class Scheduler:
    global C #link capacity
    global epoch
    
    def __init__ (self,epochx,algo,debug = False):
        global epoch
        self.debug = debug
        self.algo = algo
        epoch = float(epochx)
        self.success_count = 0
        self.reject_count = 0
        self.no_request = 0
        self.t_now = -1*epoch #initial timeslot (epoch)
        self.flows = dict() #indexed by the flow_id

        #those three lists are returned to the coordinator
        self.updated_flows = [] #tuple of source and new rate
        self.new_flows = []
        self.rejected_flows = []

        self.updated_flows_temp = dict() #because we might update a flow and then updated it again, so will keep a dictionay
        self.new_flows_temp = dict()
        self.original_flows_info = dict() 
        

    def pace(self,new_f):
        global epoch
        global C

        temp_flows = []
        for f in self.flows:
            temp_flows.append(self.flows[f]) 
            
        #sort by SJF or LJF (if you want to favor SJF, then sort by LJF and vice-versa)
        if self.algo == 'sjf':
            temp_flows.sort(key=lambda x: x.remain_data, reverse=True)
        elif self.algo == 'ljf':
            temp_flows.sort(key=lambda x: x.remain_data, reverse=False)
        else:
            print "invalid algo"

        #xx = 0
        #for ff in self.flows:
        #    xx = xx + self.flows[ff].Ralloc
        #print "before pace: the total bandwidth now",xx

        temp_sum = 0 
        involved_flows = []
        for f in temp_flows: 
            involved_flows.append(self.flows[f.flow_id]) # keep the flow original info
            temp_sum = temp_sum + (self.flows[f.flow_id].Ralloc - self.flows[f.flow_id].Rmin)

            if temp_sum >= new_f.Rmin:
                for x in involved_flows:
                    self.updated_flows_temp[x.flow_id] = (x.src,x.Ralloc)
                self.success_count = self.success_count + 1
                #this last flow don't take its whole slack, just take enough to reach RMin for new flow
                self.flows[f.flow_id].set_rate((self.flows[f.flow_id].Rmin + (temp_sum - new_f.Rmin)),self.t_now)
                if self.debug == True:
                    print "after pacing: flow",f.flow_id," Ralloc: ",self.flows[f.flow_id].Ralloc," te ",self.flows[f.flow_id].te

                new_f.set_rate(new_f.Rmin,self.t_now)
                self.flows[new_f.flow_id] = new_f
                if self.debug == True:
                    print "Success, the flow was assigned rate of ", new_f.Ralloc," Rmin ",new_f.Rmin," te ",new_f.te
                self.new_flows_temp[new_f.flow_id] = (new_f.src,new_f.Ralloc)
                #self.new_flows.append((new_f.src,new_f.Ralloc))
                #xx = 0
                #for ff in self.flows:
                #    xx = xx + self.flows[ff].Ralloc
                #print "after pace: the total bandwidth now",xx
                return
            else:
                #update flow Ralloc te slack
                self.flows[f.flow_id].set_rate(self.flows[f.flow_id].Rmin,self.t_now)
                
        #if we reached here, then we cannot pace flows and get Rmin for the new flow
        if self.debug == True:
            print "Reject, no available bandwidth even with pacing"
        self.reject_count = self.reject_count + 1
        self.revert_flow_changes(involved_flows)
        self.rejected_flows.append((new_f.src,new_f.Ralloc))

    def revert_flow_changes(self,involved_flows):
        for f in involved_flows:
            self.flows[f.flow_id] = f 

    #coordinator can give this information
    def check_flow_completed(self,f):
        if self.flows[f].te <= int(self.t_now):
            return True
        else:
            return False

    def delete_completed_flows(self):
        global epoch
        current_flows = dict() #need to make a copy to delete
        for f in self.flows:
            if self.check_flow_completed(f) == True:
                if self.debug == True:
                    print "flow",f, " finished"
                #delete the flow id from the links involved
            else:
                current_flows[f] = self.flows[f]
                current_flows[f].update(self.t_now)
        self.flows = current_flows #current_flow does not include the finished flows

    def reshape(self):        
        involved_flows = []
        for f in self.flows:
            involved_flows.append(self.flows[f])
        #sort by te
        if self.algo == 'sjf':
            involved_flows.sort(key=lambda x: x.remain_data, reverse=False)
        elif self.algo == 'ljf':
            involved_flows.sort(key=lambda x: x.remain_data, reverse=True)
        else:
            print "invalid algo"

        #give all resid bandwidth to the flow with LJ or SJ
        temp_sum = 0
        for f in self.flows:
            temp_sum = temp_sum + self.flows[f].Ralloc

        Rresid = C - temp_sum
        if Rresid > 0:
            reshaped_flow = involved_flows[0].flow_id # will take the first flow in the list 
            self.flows[reshaped_flow].set_rate(self.flows[reshaped_flow].Ralloc + Rresid,self.t_now)
            if self.debug == True:
                print "flow",reshaped_flow ,"reshaped. Ralloc = ",self.flows[reshaped_flow].Ralloc," te = ",self.flows[reshaped_flow].te
            self.updated_flows_temp[reshaped_flow] = (self.flows[reshaped_flow].src,self.flows[reshaped_flow].Ralloc)

        #xx = 0
        #for ff in self.flows:
        #    xx =xx + self.flows[ff].Ralloc
        #print "reshape: the total bandwidth now",xx

        
    def sched(self,requests):
        global epoch
        global C
        self.t_now = self.t_now + epoch
        if self.debug == True:
            print "\nt_now = ", self.t_now
        
        # re-initialize the list for the new epoch requests
        self.updated_flows = [] #tuple of source and new rate
        self.new_flows = []
        self.rejected_flows = []
        self.updated_flows_temp = dict()
        self.new_flows_temp = dict()

        # check if flow finishes or not
        self.delete_completed_flows() 
    
        #keep original flows info before reshaping/pacing
        self.original_flows_info = self.flows

        if len(self.flows) != 0:
            self.reshape() 


        if len(requests) == 0:
            #no new reuest, return empty lists
            return self.new_flows, self.rejected_flows, self.updated_flows

        for req in requests:
            self.no_request = self.no_request + 1
            new_f = flow(self.no_request,req.size,req.td,req.src,req.dst,self.t_now) # the new flow to schedul
            if self.debug == True:
                print "new request: flow",new_f.flow_id," size ",req.size,"Rmin",new_f.Rmin," td ", req.td," src,dst ",req.src,req.dst

            # find Rresidual bandwidth in the path p
            temp_sum = 0
            for f in self.flows:
                temp_sum = temp_sum + self.flows[f].Ralloc
            Rresid = C - temp_sum

            if(Rresid < new_f.Rmin):
                self.pace(new_f)
            else:
                new_f.set_rate(Rresid,self.t_now)
                self.new_flows_temp[new_f.flow_id] = (new_f.src,new_f.Ralloc)
                self.flows[new_f.flow_id] = new_f
                
                if self.debug == True:
                    print "Success, flow has been scheduled with rate ",new_f.Ralloc," te = ",new_f.te
                self.success_count = self.success_count + 1


        for f in self.updated_flows_temp:
            if f in self.new_flows_temp:
                self.new_flows_temp[f] = self.updated_flows_temp[f] 
            else:
                prev_Ralloc = self.original_flows_info[f].Ralloc
                src,new_Ralloc = self.updated_flows_temp[f]
                if prev_Ralloc == new_Ralloc: #only if Ralloc changed add it to updated_flows
                    continue
                else:
                    self.updated_flows.append(self.updated_flows_temp[f])

        for f in self.new_flows_temp:
                self.new_flows.append(self.new_flows_temp[f])

        return self.new_flows, self.rejected_flows, self.updated_flows

    def get_total_no_requests(self):
        return self.no_request

    def get_reject_rate(self):
        return (self.reject_count*1.0/self.no_request)

    def get_accept_rate(self):
        return (self.success_count*1.0/self.no_request)

#====================core classes======================

class flow:
    def __init__(self,flow_id,size,td,src,dst,t_now):
        global epoch
        self.flow_id = flow_id
        self.src = src
        self.dst =dst
        self.size = int(size*1e6*8) #unit bits
        self.td = t_now + td  #in sec
        self.te = self.td #unit in sec
        self.Rmax = int(10000*1e6) # unit bps, max rate the end points and the bottleneck link in the path can achieve
        self.Rmin = int((self.size*1.0) / (self.td - t_now)) #unit bps 
        self.Ralloc = 0
        self.slack = 0
        self.sent_data = 0 #unit bytes, data sent so far
        self.remain_data = int(self.size - self.sent_data)

    def update(self,t_now):
        global epoch
        self.sent_data = int(self.sent_data + (self.Ralloc*epoch)) #in bits  
        self.remain_data = int(((self.size - self.sent_data)))
        self.Rmin = int(self.remain_data*1.0 / ((self.td - t_now)))
        self.te = int(t_now + (self.remain_data / (self.Ralloc*1.0)))
        self.slack = self.Ralloc - self.Rmin


    def set_rate(self,rate,t_now):
        global epoch

        self.Ralloc = rate
        self.te = int(t_now + (self.remain_data/(self.Ralloc*1.0)))
        self.slack = self.Ralloc - self.Rmin

class Request:
    def __init__(self,src,dst,size,ts,td):
        self.ts = 0
        self.size = size # file size in MB
        self.td = td # deadline in seconds
        self.src = src
        self.dst = dst
    def __str__(self):
        return "src= "+self.src+" dst: "+str(self.dst)+" size: "+str(self.size)+" deadline: "+str(self.td)
    def __repr__(self):
        return self.__str__()
