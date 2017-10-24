import sys
import numpy as np
import scheduler

class traffic_gen:
    nodes = []
    C = 10000
    epoch = 1
    tot_req = 0
    np.random.seed(3)

    def __init__(self,sources,C,epoch):
        self.C = C
        self.epoch = epoch
        self.nodes = sources


    def generate_requests(self):

        td_lambda = 60*60 #1 hour
        s_lambda = 500
        arriv_rate = 0.5

        requests = []
        absolute_sum = 0
        
        inter_arrival = np.random.exponential(arriv_rate)
        absolute_sum = absolute_sum + inter_arrival
        while absolute_sum <= epoch: #(t_now+1)*epoch:
            self.tot_req = self.tot_req + 1
            td = int(np.random.exponential(td_lambda))
            while td < epoch: 
                td = int(np.random.exponential(td_lambda))
            avg_rate = np.random.exponential(s_lambda)
            size = (avg_rate * td) / 8 #unit MB
            while size < 1 or size*8/td > C:
                avg_rate = np.random.exponential(s_lambda)
                size = (avg_rate * td) / 8 #unit MB
            src = np.random.choice(self.nodes)
            dst = 0
            while dst == src:
                dst = np.random.choice(self.nodes)
            req = scheduler.Request(src,dst,size,0,td)
            requests.append(req)
            inter_arrival = np.random.exponential(arriv_rate)
            absolute_sum = absolute_sum + inter_arrival
        else:
            return requests

sources = ['CL','AMS','CLD','FF']
C = 10000 #10 Mbps
epoch = 1
gen = traffic_gen(sources,C,epoch)

sched = 'new-global' #sys.argv[2]
algo = 'ljf' ##sys.argv[3]
ver = '1' #sys.argv[4]
s = scheduler.Scheduler(epoch,algo,debug=False)


for i in range(0,100):
    requests = gen.generate_requests()
    new_flows, rejected_flows, updated_flows = s.sched(requests)
    print "new flows",new_flows
    print "rejected flows",rejected_flows
    print "updated flows",updated_flows

print "reject count = ",s.reject_count,"reject rate = ",s.reject_count/(gen.tot_req*1.0)
print "get accept rate",s.get_reject_rate()
