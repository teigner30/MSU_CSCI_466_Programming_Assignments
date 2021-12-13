import queue
import threading
from link import LinkFrame
from rprint import print


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    #  @param capacity - the capacity of the link in bps
    def __init__(self, maxsize=0, capacity=500):
        self.in_queue = queue.Queue(maxsize);
        self.out_queue = queue.Queue(maxsize);
        self.capacity = capacity #serialization rate
        self.next_avail_time = 0 #the next time the interface can transmit a packet
        self.priority_1 = 0
        self.priority_0 = 0
    
    ##get packet from the queue interface
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
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            self.out_queue.put(pkt, block)
        else:
            self.in_queue.put(pkt, block)

    def sort(self):
        # set priority counts to 0 every sort
        self.priority_0 = 0
        self.priority_1 = 0
        queuelist = {}
        for i in range(self.out_queue.qsize()):
            pkt = self.out_queue.get('out')
            queuelist[pkt] = pkt[-1]
        sorted_values = sorted(queuelist.values(), reverse=True)
        newqueuelist = {}
        for i in sorted_values:
            for k in queuelist.keys():
                if queuelist[k] == i:
                    if i == '0':
                        self.priority_0 += 1
                    else:
                        self.priority_1 += 1
                    newqueuelist[k] = queuelist[k]
                    break
        for elem in newqueuelist.keys():
            self.out_queue.put(elem)
        
## Implements a network layer packet
# NOTE: You will need to extend this class for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param priority: packet priority
    def __init__(self, dst, data_S, priority):
        self.dst = dst
        self.data_S = data_S
        self.priority = priority

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        byte_S += self.data_S
        byte_S += str(self.priority)
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        data_S = byte_S[NetworkPacket.dst_S_length : -1]
        priority = byte_S[-1]
        return self(dst, data_S, priority)

class MPLSFrame:
    ## packet encoding lengths
    dst_S_length = 5

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param priority: packet priority
    def __init__(self, label, networkPacket):
        self.label = label
        self.networkPacket = networkPacket

    ## called when printing the object
    def __str__(self):
        tostring = 'MPLSFrame' + str(self.label)
        return tostring

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.label).zfill(self.dst_S_length)
        byte_S += str(self.networkPacket)
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        label = byte_S[0: MPLSFrame.dst_S_length].strip('0')
        networkPacket = byte_S[MPLSFrame.dst_S_length:]
        return self(int(label), networkPacket)
    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    # @param priority: packet priority
    def udt_send(self, dst, data_S, priority):
        pkt = NetworkPacket(dst, data_S, priority)
        print('%s: sending packet "%s" with priority %d' % (self, pkt, priority))
        #encapsulate network packet in a link frame (usually would be done by the OS)
        fr = LinkFrame('Network', pkt.to_byte_S())
        #enque frame onto the interface for transmission
        self.intf_L[0].put(fr.to_byte_S(), 'out') 
        
    ## receive frame from the link layer
    def udt_receive(self):
        fr_S = self.intf_L[0].get('in')
        if fr_S is None:
            return
        #decapsulate the network packet
        fr = LinkFrame.from_byte_S(fr_S)
        assert(fr.type_S == 'Network') #should be receiving network packets by hosts
        pkt_S = fr.data_S
        print('%s: received packet "%s"' % (self, pkt_S))
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_capacity_L: capacities of outgoing interfaces in bps 
    # @param encap_tbl_D: table used to encapsulate network packets into MPLS frames
    # @param frwd_tbl_D: table used to forward MPLS frames
    # @param decap_tbl_D: table used to decapsulate network packets from MPLS frames
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_capacity_L, encap_tbl_D, frwd_tbl_D, decap_tbl_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size, intf_capacity_L[i]) for i in range(len(intf_capacity_L))]
        #save MPLS tables
        self.encap_tbl_D = encap_tbl_D
        self.frwd_tbl_D = frwd_tbl_D
        self.decap_tbl_D = decap_tbl_D
        

    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        prior_dict = {}
        for i in range(len(self.intf_L)):
            fr_S = None #make sure we are starting the loop with a blank frame
            fr_S = self.intf_L[i].get('in') #get frame from interface i
            if fr_S is None:
                continue # no frame to process yet
            #decapsulate the packet
            fr = LinkFrame.from_byte_S(fr_S)
            pkt_S = fr.data_S
            #process the packet as network, or MPLS
            if fr.type_S == "Network":
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                self.process_network_packet(p, i)
            elif fr.type_S == "MPLS":
                m_fr = MPLSFrame.from_byte_S(pkt_S) #parse a frame out
                str_m_fr = str(m_fr)
                prior_dict[pkt_S + str(i)] = str_m_fr[-1]


            else:
                raise('%s: unknown frame type: %s' % (self, fr.type))

        sorted_values = sorted(prior_dict.values(), reverse=True)
        newqueuelist = {}
        for i in sorted_values:
            for k in prior_dict.keys():
                if prior_dict[k] == i:
                    newqueuelist[k] = prior_dict[k]
                    break

        for elem in newqueuelist.keys():
            i = elem[-1]
            mFrame = MPLSFrame.from_byte_S(elem[0:-1])  # parse a frame out
            self.process_MPLS_frame(mFrame, int(i))


    ## process a network packet incoming to this router
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def process_network_packet(self, pkt, i):
        #for now, we just relabel the packet as an MPLS frame without encapsulation
        keyval = self.encap_tbl_D[pkt.dst]
        # came in on interface 0 so mpls label 4 or 5
        if i == 0:
            if pkt.priority == '0':
                key = list(keyval.keys())[0]
            else:
                key = list(keyval.keys())[1]
        # came in on interface 1 so 2 or 3
        else:
            if pkt.priority == '0':
                key = list(keyval.keys())[2]
            else:
                key = list(keyval.keys())[3]

        m_fr = MPLSFrame(int(key), pkt)

        print('%s: encapsulated packet "%s" as MPLS frame "%s"' % (self, pkt, m_fr))
        #send the encapsulated packet for processing as MPLS frame
        self.process_MPLS_frame(m_fr, i)


    ## process an MPLS frame incoming to this router
    #  @param m_fr: MPLS frame to process
    #  @param i Incoming interface number for the frame
    def process_MPLS_frame(self, m_fr, i):

        print('%s: processing MPLS frame "%s"' % (self, m_fr))
        key = m_fr.label
        if key in self.decap_tbl_D.keys():
            print('router', self.name)
            out = self.decap_tbl_D[key]
            # for now forward the frame out interface 1
            try:
                fr = LinkFrame('Network', m_fr.to_byte_S())
                self.intf_L[out].put(fr.to_byte_S(), 'out', True)
                print('%s: forwarding frame TO HOSTTTT "%s" from interface %d to %d' % (self, fr, i, out))
            except queue.Full:
                print('%s: frame "%s" lost on interface %d' % (self, m_fr, i))
                pass
        else:
            out1 = self.frwd_tbl_D[key]
            out = out1[key]
            try:
                fr = LinkFrame('MPLS', m_fr.to_byte_S())
                self.intf_L[out].put(fr.to_byte_S(), 'out', True)
                print('%s: forwarding frame "%s" from interface %d to %d' % (self, fr, i, out))
            except queue.Full:
                print('%s: frame "%s" lost on interface %d' % (self, m_fr, i))
                pass
        
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 