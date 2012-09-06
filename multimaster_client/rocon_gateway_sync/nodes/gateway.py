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
import rosgraph
from zeroconf_comms.msg import DiscoveredService


# This class is wrapper ros class of gateway sync.
# The role of this node is below
# 1. listens to server up/down status from zero configuration node
# 2. listens to local ros node's remote topic registration request
class Gateway():
  zeroconf_new_connection_topic = "/zeroconf/new_connections"
  zeroconf_lost_connection_topic = "/zeroconf/lost_connections" # This may not be needed
  gateway_sync = None
  param = {}

  def __init__(self):

    self.parse_params()

    # Instantiate a GatewaySync module. This will take care of all redis server connection, communicatin with ros master uri
#self.gateway_sync = GatewaySync()

    # Subscribe from zero conf new connection
    self.new_connectin_sub = rospy.Subscriber(self.zeroconf_new_connection_topic,DiscoveredService,self.processServerConnection)

  def parse_params(self):

    # Local topics and services to register redis server
    self.param['local_public_topic'] = rospy.get_param('~local_public_topic','')
    self.param['local_public_service'] = rospy.get_param('~local_public_service','')

    # Topics and services that need from remote server
    self.param['remote_topic'] = rospy.get_param('~remote_topic','')
    self.param['remoteservice'] = rospy.get_param('~remote_service','')


    
  def processServerConnection(self,msg):
    rospy.loginfo("Redis Server is discovered = " + str(msg.ipv4_addresses[0]) + ":"+str(msg.port))

    # Connects to Redis server
    #ret = self.gateway_sync.connectToRedisServer(msg.ipv4_addresses,msg.port)
#if not ret :
#    print rospy.loginfo("Failed to connect Redis Server")
#     return

    # self.gateway_sync.setDefaultSetup(self.param)

  def spin(self):
    rospy.spin()


if __name__ == '__main__':
  
  rospy.init_node('multimaster_gateway')

  gateway = Gateway()
  rospy.loginfo("Initilized")

  gateway.spin()

