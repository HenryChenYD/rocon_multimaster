#!/usr/bin/env python
#       
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/multimaster_client/rocon_gateway/LICENSE 
#

import rospy
import threading
from gateway_comms.msg import Connection

class WatcherThread(threading.Thread):
    '''
    '''
    
    def __init__(self,gateway):
        # init thread
        threading.Thread.__init__(self)
        self.gateway = gateway
        self.master = gateway.master
        self.cv = self.master.cv
        self.pubs = self.master.pubs_node
        self.public_interface = gateway.public_interface
        self.flipped_interface = gateway.flipped_interface

    
        self.start()

    def run(self):
        while not rospy.is_shutdown():
            self.cv.acquire()

            if self.gateway.is_connected:
                connections = self.master.getConnectionState()
                new_flips, lost_flips = self.flipped_interface.update(connections)
                # do whatever we need to do on the redis server here
                self.gateway.updatePublicInterface()
            self.cv.release()
            rospy.sleep(3.0)

    def _updatePublicInterface(self, connections):
        '''
          Process the list of local connections and check against 
          the current rules and patterns for flips. If a connection 
          has become (un)available take appropriate action.
          
          @param connections
          @type dictionary of connections 
        '''



        for connection_type in connections:
            allowed_connections = self.public_interface.allowedConnections(connections[connection_type])
            
            # this has both connections that have disappeared or are no longer allowed
            public_connections = set([x for x in self.public_interface.public if x.type == connection_type])
            advertise_new_connections = allowed_connections - public_connections
            unadvertise_connections = public_connections - allowed_connections

            for connection in advertise_new_connections:
                self.gateway.advertiseConnection(connection)

            for connection in unadvertise_connections:
                self.gateway.unadvertiseConnection(connection)
    
    def update(self, type, connections):
        # CURRENTLY DISABLED (work in progress)
        # unadvertise from public interface if a topic disappears from the local master
        # for string in self.public_interface.interface[identifier]:
        #     name, _, node_uri = string.split(",")
        #     still_exist = False
        #     try:
        #         llist = [x[1] for x in list if x[0] == name]
        #
        #         # all nodes are gone.
        #         uris = [self.master.lookupNode(p) for p in llist[0]]
        #         still_exist = node_uri in uris
        #     except:
        #         still_exist = False
        #       
        #     # if it is not exist anymore, remove it from public interface
        #     if not still_exist:
        #         self.gateway.unadvertise([string])
        #
        # # add/remove named interfaces to public list as necessary
        # for x in list:
        #     name = x[0]
        #     if self.gateway_sync.allowInterfaceInPublic(identifier, name):
        #         # check if any new publishers are available
        #         self.gateway_sync.addPublicInterfaceByName(identifier, name)
        #         self.dumped_interface[identifier].add(name)
        #     else:
        #         # this interface has been dumped in the past, and is no longer needed
        #         if name in self.dumped_interface[identifier]:
        #             self.gateway.removePublicInterfaceByName(identifier, name)
        #             self.dumped_interface[identifier].remove(name)
  
        # DJS: CURRENTLY DISABLED (work in progress)
        # add/remove named interfaces to flipped list as necessary
        # for x in list:
        #     name = x[0]
        #     clients, non_clients = self.gateway.getFlippedClientList(identifier, name)
        #     self.gateway.addFlippedInterfaceByName(identifier,clients,name)
        #     self.gateway.removeFlippedInterfaceByName(identifier,non_clients,name)
        pass
