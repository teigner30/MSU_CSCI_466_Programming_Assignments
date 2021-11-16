import queue
import threading
from rprint import print


# wrapper class for a queue of packets
class Interface:
    # @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    # get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
    
    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


# Implements a network layer packet.
class NetworkPacket:
    # packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1
    
    # @param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S
    
    # called when printing the object
    def __str__(self):
        return self.to_byte_S()
    
    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise ('%s: unknown prot_S option: %s' % (self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0: NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length: NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise ('%s: unknown prot_S field: %s' % (self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length:]
        return self(dst, prot_S, data_S)


# Implements a network host for receiving and transmitting data
class Host:
    
    # @param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination
    
    # called when printing the object
    def __str__(self):
        return self.addr
    
    # create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully
    
    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
    
    # thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if (self.stop):
                print(threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router
class Router:
    
    # @param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        # save neighbors and interfaces on which we connect to them
        self.cost_D = cost_D  # {neighbor: {interface: cost}}
        # TODO: set up the routing table for connected hosts
        self.rt_tbl_D = {}  # {destination: {router: cost}}

        print('costsss', self.name, self.cost_D)
        # setting up the routing table
        for neighbor, cost in cost_D.items():
            for k, v in cost.items():
                self.rt_tbl_D[neighbor] = {self.name: v}
        self.rt_tbl_D[self.name] = {self.name: 0}
        print('%s: Initialized routing table' % self)
        self.print_routes()

        # send to the neighbors, which are in cost_D

    # Print routing table
    def print_routes(self):
        print(self.rt_tbl_D)
        print("Routing table at %s" % self.name)
        # TODO: print the routes as a two dimensional table
        print('==========================')
        print('|', self.name, '| ', end='')
        for destination, value in self.rt_tbl_D.items():
            print(destination, '| ', end='')
            router = list(value.keys())
        print('')
        print('==========================')

        for r in router:
            print('| ', end='')
            print(r, '| ', end='')
            for destination, value in self.rt_tbl_D.items():
                for router, cost in value.items():
                    if router == r:
                        print(cost, ' | ', end='')


            print('')
            print('--------------------------')



    
    # called when printing the object
    def __str__(self):
        return self.name
    
    # look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p, i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
    
    # forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the 
            #  forwarding table to find the appropriate outgoing interface
            #  for now we assume the outgoing interface is 1
            dest = p.dst

            costs = {}
            # find the router with the minimum cost for the destination
            for router, cost in self.rt_tbl_D[dest].items():
                costs[router] = cost
            mini = min(costs, key=costs.get)

            # get the interface for this router and send on this interface
            for neighbor, info in self.cost_D.items():
                for interface, cost in info.items():
                    if neighbor == mini:
                        self.intf_L[interface].put(p.to_byte_S(), 'out', True)
                        print('%s: forwarding packet "%s" from interface %d to %d' % (self, p, i, interface))

        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass
    
    # send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # TODO: Send out a routing table update
        #  create a routing table update packet
        data = self.name
        data += ' '
        for destination, value in self.rt_tbl_D.items():
            data += destination + ' '
            for router, cost in value.items():
                data += router
                data += str(cost)
                data += '$ '+ destination + ' '
            data = data[0:-(len(destination)+1)]
            data += ' '
        print(data)
        p = NetworkPacket(0, 'control', data)
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass
    
    # forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        # print("BEGINNING", self.rt_tbl_D)
        # TODO: add logic to update the routing tables and
        #  possibly send out routing updates
        updated = False
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        data = p.data_S.split('$')
        datalist = []
        for d in data:
            datalist.append(d.split(' '))
        from_router = datalist[0][0]
        del datalist[0][0]
        newlist = [x for x in datalist if x]
        for d in newlist:
            while '' in d:
                d.remove('')
        newestlist = [x for x in newlist if x]
        for d in newestlist:
            if len(d) == 2:
                name = d[1]
                newname = name[0:2]
                if '100' in name:
                    cost = 100
                else:
                    cost = int(name[-1])
                if 'H' in d[0]:
                    if d[0] not in self.rt_tbl_D.keys():  # if the new host isn't in the table already, we add it with infinte cost to ourselves
                        self.rt_tbl_D[d[0]] = {self.name: 100}
                        if newname in self.rt_tbl_D.keys():  # IF The router is a destionation, we know it's a neighbor and we know the cost so we set it!
                            self.rt_tbl_D[d[0]][newname] = cost
                        for neighbor in self.cost_D.keys():
                            if neighbor not in self.rt_tbl_D[d[0]].keys() and 'H' not in neighbor:
                                self.rt_tbl_D[d[0]][neighbor] = 100
                        updated = True
                    else:    # if the host is in our table
                        if newname in self.rt_tbl_D.keys():
                            currcost = self.rt_tbl_D[d[0]][newname]  # if the new update has a lesser cost than our table
                            if currcost > cost:
                                self.rt_tbl_D[d[0]][newname] = cost
                                updated = True
                #  if it is not a host, and it is a NEIGHBOR router and we don't have it as a router
                elif d[0] in self.rt_tbl_D.keys():
                    for dest, val in self.rt_tbl_D.items():
                        if newname in self.rt_tbl_D.keys():  # if the router is a neighbor
                            if newname not in val.keys():  # if we don't have the router in our routing table as a router
                                if dest == d[0]:  # if the destinatin is whats in the message, we know the cost
                                    self.rt_tbl_D[dest][newname] = cost
                                elif dest == newname:  # if the destination and router are the same it should be 0
                                    self.rt_tbl_D[dest][newname] = 0
                                else:  # otherwise, we don't know
                                    self.rt_tbl_D[dest][newname] = 100
                                updated = True
                            else:
                                currcost = self.rt_tbl_D[d[0]][newname]
                                if currcost > cost:
                                    self.rt_tbl_D[d[0]][newname] = cost
                                    updated = True
                # if d[0] in self.rt_tbl_D.keys():
                #     if newname in self.rt_tbl_D[d[0]].keys():
                #         curr_cost = self.rt_tbl_D[d[0]][newname]
                #         if curr_cost > cost:
                #             self.rt_tbl_D[d[0]][newname] = cost
                #             updated = True
        routers = []
        for neigh in self.cost_D.keys():
            if 'H' not in neigh:
                routers.append(neigh)
        for destination, value in self.rt_tbl_D.items():
            for r in routers:
                if r not in value.keys():
                    self.rt_tbl_D[destination][r] = 100
                    if destination == r:
                        self.rt_tbl_D[destination][r] = 0
                    updated = True
        if updated:
            # print(self.name, self.rt_tbl_D)
            # print('init updated')
            # print("ROUTERSS", routers)
            for neighbor, value in self.cost_D.items():
                for interface, cost in value.items():
                    # if neighbor in routers:
                    self.send_routes(interface)


        # find the minimum cost for the destionation
        # if the minimum cost is different than what it is now, updated = True
        else:
            # print('start bellman ford')
            for destination, value in self.rt_tbl_D.items():

                for curr_router in value.keys():
                    dist_list = {}
                    if curr_router == destination:
                        continue
                    elif curr_router == self.name:
                        neighbors = []
                        key = self.cost_D.keys()
                        for neighbor in key:
                            neighbors.append(neighbor)
                        neighbors.append(curr_router)
                    else:  ## add the currrouter to the neighbor list in the case in we're the routing table that we're loooking at
                        neighbors = [self.name, curr_router]
                    for n in neighbors:
                        if 'H' not in n:  # to avoid hosts
                            # print(self.name, self.rt_tbl_D, 'neighbor', n, destination)
                            # if curr_router == self.name:
                            #     # for k in self.cost_D[n].values():
                            #     #     # print(len(self.cost_D[n]), 'LENGOTH OF COST K')
                            #     dist_list[n] = self.rt_tbl_D[n][curr_router] + self.rt_tbl_D[destination][n]
                            # else:
                            dist_list[n] = self.rt_tbl_D[n][curr_router] + self.rt_tbl_D[destination][n]
                    if not dist_list:
                        continue
                    # print('LIST OF COMPARABLES \nME', self.name, '\ndest: ', destination, '\nrouter:',curr_router, '\n',dist_list,'\n',self.rt_tbl_D, '\nneighbors', neighbors)
                    minim = min(dist_list, key=dist_list.get)
                    # self.rt_tbl_D[self.name][destination] = dist_list[minim]
                    if self.rt_tbl_D[destination][curr_router] > dist_list[minim]:
                        self.rt_tbl_D[destination][curr_router] = dist_list[minim]
                        # print("SOMETHING", self.rt_tbl_D[destination][self.name])
                        # print("UPdating in bellmans style", self.name)
                        updated = True
            #
            #
            #
            #
            if updated:
                # print("ROUTERSS", routers)
                for neighbor, value in self.cost_D.items():
                    for interface, cost in value.items():
                        # if neighbor in routers:
                        self.send_routes(interface)



                    # if newname in self.rt_tbl_D[d[0]].keys():
                    #     if self.rt_tbl_D[d[0]][newname] != cost:  # if there is information in here already, we check to see if we should update it
                    #
                    #         self.rt_tbl_D[d[0]][newname] = cost
                    #         updated = True
                    # else:  # if new router isn't in this table, we add it
                    #     self.rt_tbl_D[d[0]][newname] = cost
                    #     updated = True
                            # self.rt_tbl_D[d[0]][self.name] = 100  # if the destination isn't in our routing table, our cost to it is infinite
                            # for neighbor in self.cost_D.keys():  # if we have another neighbor, we have to add their cost to the destination which is unknown??????
                            #     if neighbor != newname and 'H' not in neighbor:
                            #         self.rt_tbl_D[d[0]][neighbor] = 100
                            # # print("UPdating in initialization")

        # print(self.name, 'MINE', 'from', from_router, self.rt_tbl_D)

        # for destination, value in self.rt_tbl_D.items():   # this gets a list of the routers that are currently in the values for initialization
        #     for rout in value.keys():
        #         if rout not in routers:
        #             routers.append(rout)
        # # print('routem', routers)
        # for destination, value in self.rt_tbl_D.items():   # this sets the the rest of the values that need to be filled in to be 100. A lot of these 100's should be updated later when we do the minimimum stuff
        #     for r in routers:
        #         if r not in value.keys():
        #             self.rt_tbl_D[destination][r] = 100
        #             # print("UPdating in lower initialization")
        #             updated = True
        # if updated:
        #     print("updated in init", self.name, 'MINE innit??', self.rt_tbl_D)


        # confusing stuff :) vvvv

        # for destination, value in self.rt_tbl_D.items():
        #     if destination == self.name:
        #         continue
        #     dist_list = {}

            # for neighbor, c in self.cost_D.items():
            #     for cost in c.values():
            #         if 'H' not in neighbor:
            #             if neighbor in value.keys():
            #                 print('we in')

            # for d in newestlist:
            #
            #     if len(d) == 2:
            #
            #         dest = d[0]
            #         # print('this is d', dest, 'destination', destination)
            #         if dest == destination:   # if the destination from the message is the destination we're looking at, we want to do stuff
            #             # print('destinatino is good', d)
            #             part2 = d[1]
            #             routermess = part2[0:2]
            #             if destination == routermess:
            #                 if '100' in part2:
            #                     costmess = 100
            #                 else:
            #                     costmess = int(part2[-1])
            #                 dist_list[routermess] = costmess
            #             elif routermess in self.cost_D.keys():
            #                 # print('router from message is neighbor', d)
            #                 if '100' in part2:
            #                     costmess = 100
            #                 else:
            #                     costmess = int(part2[-1])
            #                 for cost in self.cost_D[routermess].values():
            #                     dist_list[routermess] = cost + costmess
            #                 # print('distLIST', dist_list)
            #             # else:
            #             #     dist_list[neighbor] = cost + self.rt_tbl_D[destination][neighbor]
            # for router, cost in value.items():
            #     if router in dist_list.keys():
            #         messagecost = dist_list[router]
            #         ourcost = cost + self.rt_tbl_D[router][self.name]
            #         if messagecost < ourcost:  # if message had smaller cost, then we update our table
            #             self.rt_tbl_D[destination][router] = messagecost
            #             print('from router', from_router ,"UPdating not in costs", self.name,  destination, router, messagecost, ourcost)
            #             updated = True
            #             cost = messagecost
            #         else:
            #             cost = ourcost
            #         dist_list[router] = cost
            #     # if router != destination:
            #     else:
            #         dist_list[router] = cost + self.rt_tbl_D[router][self.name]
            #     # else:
            #     #     dist_list[router] = cost
            # if not dist_list:
            #     # print("dist-list is emtpy", dist_list)
            #     continue
            # # else:
            # #
            # #     print('distlist is exciting', dist_list)
            # minim = min(dist_list, key=dist_list.get)
            # # self.rt_tbl_D[self.name][destination] = dist_list[minim]
            # if self.rt_tbl_D[destination][self.name] != dist_list[minim]:
            #     self.rt_tbl_D[destination][self.name] = dist_list[minim]
            #     # print("SOMETHING", self.rt_tbl_D[destination][self.name])
            #     print("UPdating in bellmans style", self.name)
            #     updated = True






                    # else:
                    #     if newname in self.rt_tbl_D[d[0]].keys():  #if the router is already in the current destination's key
                    #         curr_cost = self.rt_tbl_D[d[0]][newname]
                    #         add_cost = 0
                    #         if d[0] not in self.cost_D.keys(): # if the destination is not a neighbor, we have to get the distance from ourselves to the router
                    #             add_cost = self.rt_tbl_D[newname][self.name]
                    #         cost += add_cost
                    #         if curr_cost > cost:  # if the new cost is less, we update table
                    #             self.rt_tbl_D[d[0]][newname] = cost
                    #             updated = True
                    #     else:
                    #         self.rt_tbl_D[d[0]][newname] = cost
                    #         updated = True
        #
        #
        #
        # routers = []
        # # if the table is incomplete, we add 100 cost to where we don't know
        # for destination, value in self.rt_tbl_D.items():
        #     if 'H' not in destination:
        #         routers.append(destination)
        #     if destination not in value.keys():
        #         self.rt_tbl_D[destination][from_router] = 100
        #         if 'H' not in destination:
        #             self.rt_tbl_D[destination][destination] = 0
        #         updated = True
        #     if self.name not in value.keys():
        #         self.rt_tbl_D[destination][self.name] = 100
        #         updated = True

        # print("route em", routers)
        # for destination, value in self.rt_tbl_D.items():
        #     for r in routers:
        #         if r not in value.keys():
        #             self.rt_tbl_D[destination][r] = 100
        # #dist_list = {}
        # for destination, value in self.rt_tbl_D.items():
        #     dist_list = {}
        #     #print('dest,vale', destination, value, self.rt_tbl_D)
        #     #routers = value.keys()
        #     #for r in routers:
        #     for neighbor, info in self.cost_D.items():
        #         for interface, cost in info.items():
        #             if neighbor != destination:
        #                 if neighbor in value.keys():
        #                     dist_list[neighbor] = cost + self.rt_tbl_D[destination][neighbor]
        #                     #print("DIst list", dist_list)
        #                 else:
        #                     break
        #             else:
        #                 dist_list[neighbor] = cost
        #
        #     minim = min(dist_list, key=dist_list.get)
        #     #self.rt_tbl_D[self.name][destination] = dist_list[minim]
        #     if self.rt_tbl_D[destination][self.name] != dist_list[minim]:
        #         self.rt_tbl_D[destination][self.name] = dist_list[minim]
        #         print("SOMETHING", self.rt_tbl_D[destination][self.name])
        #         updated = True



            #
            #     if destination in self.cost_D.keys() and r == self.name:
            #         val = self.cost_D[destination]
            #         for k, v in val.items():
            #             costs[r] = v + self.rt_tbl_D[self.name][r]
            #     else:
            #         costs[r] = self.rt_tbl_D[destination][r] + self.rt_tbl_D[self.name][r]
            # mini = min(costs, key=costs.get)
            # if self.rt_tbl_D[destination][self.name] != costs[mini]:
            #     self.rt_tbl_D[destination][self.name] = costs[mini]
            #     updated = True
        #
        # #   to forward to the good routers
        # if updated:
        #     # print("ROUTERSS", routers)
        #     for neighbor, value in self.cost_D.items():
        #         for interface, cost in value.items():
        #             # if neighbor in routers:
        #             self.send_routes(interface)
        # else:
        #     print("WE WIN", self.name)

                    # interface = value.keys()
                    # print("INTERFACE", interface)
                    # self.send_routes(interface[0])

            # for r in routers:
            #     if r in self.cost_D.keys():
            #         print("THIS IS routers", r)
            #         for k in self.cost_D[r].keys():
            #             print("printk ", k)
            #             self.send_routes(k)

        # print("ENd", self.rt_tbl_D)

    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return
