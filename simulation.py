from network import Router, Host
from link import Link, LinkLayer
import threading
from time import sleep
from rprint import print

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 10 #give the network sufficient time to execute transfers

if __name__ == '__main__':
    object_L = [] #keeps track of objects, so we can kill their threads at the end
    
    #create network hosts
    host_1 = Host('H1')
    object_L.append(host_1)
    host_2 = Host('H2')
    object_L.append(host_2)
    # encapsulating, look at the packet
    # cannot look at the packet during forwarding

    #^^ this is really important
    #create routers and routing tables for connected clients (subnets)
    encap_tbl_D = { 'H2':{3:1},
                    'H1':{2:0}
                    }    # table used to encapsulate network packets into MPLS frames
    frwd_tbl_D = {3:{3:1},
                   2:{2:0}}     # table used to forward MPLS frames
    decap_tbl_D = { 2:0 }    # table used to decapsulate network packets from MPLS frames
    router_a = Router(name='RA', 
                              intf_capacity_L=[500,500],
                              encap_tbl_D = encap_tbl_D,
                              frwd_tbl_D = frwd_tbl_D,
                              decap_tbl_D = decap_tbl_D, 
                              max_queue_size=router_queue_size)
    object_L.append(router_a)

    encap_tbl_D = { 'H1':{2:0},
                    'H2':{3:1}}
    frwd_tbl_D = {3:{3:1},
                   2:{2:0} }
    decap_tbl_D = {3:1}
    router_b = Router(name='RB', 
                              intf_capacity_L=[500,100],
                              encap_tbl_D = encap_tbl_D,
                              frwd_tbl_D = frwd_tbl_D,
                              decap_tbl_D = decap_tbl_D,
                              max_queue_size=router_queue_size)
    object_L.append(router_b)
    
    #create a Link Layer to keep track of links between network nodes
    link_layer = LinkLayer()
    object_L.append(link_layer)
    
    #add all the links - need to reflect the connectivity in cost_D tables above
    link_layer.add_link(Link(host_1, 0, router_a, 0))
    link_layer.add_link(Link(router_a, 1, router_b, 0))
    link_layer.add_link(Link(router_b, 1, host_2, 0))
    
    
    #start all the objects
    thread_L = []
    for obj in object_L:
        thread_L.append(threading.Thread(name=obj.__str__(), target=obj.run)) 
    
    for t in thread_L:
        t.start()
    
    #create some send events    
    for i in range(5):
        priority = i%2
        host_1.udt_send('H2', 'MESSAGE_%d_FROM_H1' % i, priority)
        
    #give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)

    
    #join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()
        
    print("All simulation threads joined")