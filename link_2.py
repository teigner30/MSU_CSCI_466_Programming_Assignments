"""
Created on Oct 12, 2016

@author: mwittie
"""

import queue
import threading
from rprint import print


# An abstraction of a link between router interfaces
class Link:
    
    # creates a link between two objects by looking up and linking node interfaces.
    # @param from_node: node from which data will be transfered
    # @param from_intf_num: number of the interface on that node
    # @param to_node: node to which data will be transfered
    # @param to_intf_num: number of the interface on that node
    # @param mtu: link maximum transmission unit
    def __init__(self, from_node, from_intf_num, to_node, to_intf_num, mtu):
        self.from_node = from_node
        self.from_intf_num = from_intf_num
        self.to_node = to_node
        self.to_intf_num = to_intf_num
        self.in_intf = from_node.out_intf_L[from_intf_num]
        self.out_intf = to_node.in_intf_L[to_intf_num]
        # configure the MTUs of linked interfaces
        self.in_intf.mtu = mtu
        self.out_intf.mtu = mtu
    
    # called when printing the object
    def __str__(self):
        return 'Link %s-%d to %s-%d' % (self.from_node, self.from_intf_num, self.to_node, self.to_intf_num)
    
    # transmit a packet from the 'from' to the 'to' interface
    def tx_pkt(self):
        # go through the packets:
        #   identification number should be the same
        #   flag is 1 for last packet in segmentation
        #   frag_offset increases with each packet segment
        #   data is split, duh
        pkt_S = self.in_intf.get()
        packets = []
        if pkt_S is None:
            return  # return if no packet to transfer
        if len(pkt_S) > self.in_intf.mtu:
            i = 0
            start = 8
            finish = self.in_intf.mtu
            pkt_frag = pkt_S[0:6] + '0' + str(i) + pkt_S[start:finish]
            packets.append(pkt_frag)
            start += self.in_intf.mtu - 8
            finish += start - 8
            i += 1
            # gets all but the last segment so that we can change flag for the last one
            while start < len(pkt_S) - self.in_intf.mtu -1:

                pkt_frag = pkt_S[0:6] + '0' + str(i) + pkt_S[start:finish]
                # print('pkt frag', pkt_frag)
                packets.append(pkt_frag)
                start = finish
                finish += self.in_intf.mtu -8

                i += 1

            pkt_frag = pkt_S[0:6] + '1' + str(i) + pkt_S[start:]
            packets.append(pkt_frag)
            # print('packets list', packets)
            # print(pkt_S, ' pkt 2', pkt_S2)
            # return  # return without transmitting if packet too big
        elif len(pkt_S) > self.out_intf.mtu:
            i = 0
            start = 8
            finish = self.out_intf.mtu
            pkt_frag = pkt_S[0:6] + '0' + str(i) + pkt_S[start:finish]
            packets.append(pkt_frag)
            start += self.out_intf.mtu - 8
            finish += start - 8
            i += 1
            # gets all but the last segment so that we can change flag for the last one
            while start < len(pkt_S) - self.out_intf.mtu - 1:
                pkt_frag = pkt_S[0:6] + '0' + str(i) + pkt_S[start:finish]
                # print('pkt frag', pkt_frag)
                packets.append(pkt_frag)
                start = finish
                finish += self.out_intf.mtu - 8

                i += 1

            pkt_frag = pkt_S[0:6] + '1' + str(i) + pkt_S[start:]
            packets.append(pkt_frag)
        elif len(pkt_S) <= self.in_intf.mtu and len(pkt_S) <= self.out_intf.mtu:
            packets.append(pkt_S)
            # print('packets list', packets)
        # otherwise transmit the packet
        try:
            # print('pakceterts', packets)
            # self.out_intf.put(packets[0])
            for p in packets:
                self.out_intf.put(p)
                print('%s: transmitting packetss "%s"' % (self, p))

        except queue.Full:
            print('%s: packet lost' % (self))
            pass


# An abstraction of the link layer
class LinkLayer:
    
    def __init__(self):
        # list of links in the network
        self.link_L = []
        self.stop = False  # for thread termination
    
    # Return a name of the network layer
    def __str__(self):
        return "Network"
    
    # add a Link to the network
    def add_link(self, link):
        self.link_L.append(link)
    
    # transfer a packet across all links
    def transfer(self):
        for link in self.link_L:
            link.tx_pkt()
    
    # thread target for the network to keep transmitting data across links
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # transfer one packet on all the links
            self.transfer()
            # terminate
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return
