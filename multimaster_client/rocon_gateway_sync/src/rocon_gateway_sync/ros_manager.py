#!/usr/bin/env python       
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Yujin Robot, Daniel Stonier, Jihoon Lee
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Yujin Robot nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import roslib; roslib.load_manifest('rocon_gateway_sync')
import rospy
import rosgraph.masterapi
import time
import rostopic
import rosservice
import rosnode
import roslib.names
import itertools
import socket
import os
import threading
from cleanup_thread import CleanupThread
from .gateway_handler import GatewayHandler

class ROSManager(object):

  # xml rpc node
  node = None
  port = 0

  def __init__(self):
    rospy.loginfo("init ROS manager")

    # run xml rpc node
    # self.createXMLRPCNode()

    # Get the current node name
    self.name = rospy.get_name()
    # get Master
    self.master = rosgraph.Master(self.name)
    self.pubs_uri = {}
    self.pubs_node = {}
    self.srvs_uri = {}
    self.srvs_node = {}
    self.cv = threading.Condition()

    # create a thread to clean-up unavailable topics
    self.cleanup_thread = CleanupThread(self)

    self.getSystemState = self.master.getSystemState()

  def createXMLRPCNode(self):
    self.handler = GatewayHandler()
    self.node = rosgraph.xmlrpc.XmlRpcNode(port=self.port,rpc_handler=self.handler,on_run_error=self._xmlrpc_node_error_handler) # Can also pass port and run_error handlers
    self.node.start()

    # poll for initialization
    timeout = time.time() + 5
    while time.time() < timeout and self.node.uri is None and not rospy.is_shutdown():
        time.sleep(0.01)
    if self.node.uri is None:
        # Some error handling here
        return


  def getMasterUri(self):
    return rosgraph.get_master_uri()

  def getTopicInfo(self,topic):
    infolist = []
    topictype, _1, _2 = rostopic.get_topic_type(topic)
    try:
      pubs, _1, _2 = self.master.getSystemState()
      pubs = [x for x in pubs if x[0] == topic]

      if not pubs:
        raise Exception("Unknown topic %s"%topic)

      for p in itertools.chain(*[l for x, l in pubs]):
        info = topictype + "," + rostopic.get_api(self.master,p)
        infolist.append(info)
      
    except Exception as e:
      print "getTopicInfo"
      raise e

    return infolist

  def getServiceInfo(self,service):
    try:
      info = ""
      srvuri = rosservice.get_service_uri(service)
      nodename = rosservice.get_service_node(service)
      nodeuri = rosnode.get_api_uri(self.master,nodename)

      info = srvuri + "," + nodeuri

    except Exception as e:
      print "Error in getServiceInfo"
      raise e

    return info

  def registerTopic(self,topic,topictype,uri):
    try:
      if self.checkIfItisLocal(topic,uri,"topic"):
        print "It is local topic"
        return
        
      node_name = self.getAnonymousNodeName(topic)    
      print "New node name = " + str(node_name)

      # Initialize if it is a new topic
      if topic not in self.pubs_uri.keys():
        self.pubs_uri[topic] = [] 
        self.pubs_node[topic] = [] 
        
        
      self.cv.acquire()
      if uri  not in self.pubs_uri[topic]:
        self.pubs_uri[topic].append(uri)
        self.pubs_node[topic].append(node_name)
        master = rosgraph.Master(node_name)
        master.registerPublisher(topic,topictype,uri)
      else:
        print "already registered"
      self.cv.release()

    except Exception as e:
      print "In registerTopic"
      raise

    return

  def registerService(self,service,service_api,node_xmlrpc_uri):
    try:                                                  
      if self.checkIfItisLocal(service,node_xmlrpc_uri,"service"):
        print "It is local service"
        return
      node_name = self.getAnonymousNodeName(service)    
      print "New node name = " + str(node_name)

      # Initialize if it is a new topic
      if service not in self.srvs_uri.keys():
        self.srvs_uri[service] = [] 
        self.srvs_node[service] = [] 
        
        
      self.cv.acquire()
      if service_api not in self.srvs_uri[service]:
        self.srvs_uri[service].append(service_api)
        self.srvs_node[service].append(node_name)
        master = rosgraph.Master(node_name)
        master.registerService(service,service_api,node_xmlrpc_uri)
      else:
        print "already registered"
      self.cv.release()

    except Exception as e:
      print "registerService:ros_master.py"
      raise

    return

  def getAnonymousNodeName(self,topic):
    t = topic[1:len(topic)]
    name = roslib.names.anonymous_name(t)
    return name

  def checkIfItisLocal(self,name,uri,identifier):
    pubs, _1, srvs = self.master.getSystemState()

    if identifier == "topic":
      for p in itertools.chain(*[l for x, l in pubs]):
        uri_m = rostopic.get_api(self.master,p)

        if uri_m == uri:
          return True

    elif identifier == "service":
      nodename = rosservice.get_service_node(name)
    
      if not nodename:
        return False

      nodeuri = rosnode.get_api_uri(self.master,nodename)

      if nodeuri == uri:
        return True
    else:
      print "Wrong Identifier in checkIfItisLocal"

    return False

  """
  def getSystemState(self):
    topic_ignorelist = ["rosout", "rosout_agg", "parameter_descriptions","paramdeter_updates"]
    srv_ignorelst = ["get_loggers","seg_loggers_level"]

    pub, sub, srv = self.ros_manager.getSystemState()
  """




  def clear(self):
    self.pubs_node = {}
    self.pubs_uri = {}


  def _xmlrpc_node_error_handler(self, e): 
    ''' 
    Handles exceptions of type 'Exception' thrown by the xmlrpc node.
    '''
    # Reproducing the xmlrpc node logic here so we can catch the exception
    if type(e) == socket.error:
      (n,errstr) = e 

    #if n == 98: # can't start the node because the port is already used
    # save something to that the class can look up the problem later
    else:
      print("Xmlrpc Node Error")


