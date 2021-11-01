"""
Created on Oct 12, 2016

@author: mwittie
"""

import network
import link
import threading
from time import sleep
from rprint import print


# configuration parameters
router_queue_size = 0  # 0 means unlimited
simulation_time = 12  # give the network sufficient time to transfer all packets before quitting

if __name__ == '__main__':
	object_L = []  # keeps track of objects, so we can kill their threads
	# # need 4 hosts and 4 routers
	routing_table_a = {
		3: 0,
		4: 1
	}
	routing_table_b = {
		3: 0
	}
	routing_table_c = {
		4: 0
	}
	routing_table_d = {
		3: 0,
		4: 1
	}
	# create network nodes
	host1 = network.Host(1)
	object_L.append(host1)
	host2 = network.Host(2)
	object_L.append(host2)
	host3 = network.Host(3)
	object_L.append(host3)
	host4 = network.Host(4)
	object_L.append(host4)
	router_a = network.Router(name='A', intf_count=2, max_queue_size=router_queue_size, routing_table=routing_table_a)
	object_L.append(router_a)
	router_b = network.Router(name='B', intf_count=1, max_queue_size=router_queue_size, routing_table=routing_table_b)
	object_L.append(router_b)
	router_c = network.Router(name='C', intf_count=1, max_queue_size=router_queue_size, routing_table=routing_table_c)
	object_L.append(router_c)
	router_d = network.Router(name='D', intf_count=2, max_queue_size=router_queue_size, routing_table=routing_table_d)
	object_L.append(router_d)

	
	# create a Link Layer to keep track of links between network nodes
	link_layer = link.LinkLayer()
	object_L.append(link_layer)
	
	# add all the links
	# link parameters: from_node, from_intf_num, to_node, to_intf_num, mtu
	link_layer.add_link(link.Link(host1, 0, router_a, 0, 30))
	link_layer.add_link(link.Link(host2, 0, router_a, 1, 30))
	link_layer.add_link(link.Link(router_a, 0, router_b, 0, 30))
	link_layer.add_link(link.Link(router_a, 1, router_c, 0, 30))
	link_layer.add_link(link.Link(router_b, 0, router_d, 0, 30))
	link_layer.add_link(link.Link(router_c, 0, router_d, 1, 30))
	link_layer.add_link(link.Link(router_d, 0, host3, 0, 30))
	link_layer.add_link(link.Link(router_d, 1, host4, 0, 30))
	
	# start all the objects
	thread_L = [threading.Thread(name=object.__str__(), target=object.run) for object in object_L]
	for t in thread_L:
		t.start()

	ident = 0
	# create some send events
	# message = 'there once was a man'
	message = 'there once was a man on top of a hill, he liked to jump, he liked to write with a quill, ' \
			  'and upon his window sill, there sat a plant named bill'
	print('sending message')
	host1.udt_send(3, ident, 1, 0, message)
	# host2.udt_send(4, ident, 1, 0, message)
	ident += 1
	
	# give the network sufficient time to transfer all packets before quitting
	sleep(simulation_time)
	
	# join all threads
	for o in object_L:
		o.stop = True
	for t in thread_L:
		t.join()
	
	print("All simulation threads joined")
