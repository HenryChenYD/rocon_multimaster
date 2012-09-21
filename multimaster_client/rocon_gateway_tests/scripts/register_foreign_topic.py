#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Yujin Robot, Jihoon Lee
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

import roslib; roslib.load_manifest('rocon_gateway_tests')
import rospy
from gateway_comms.msg import *
from gateway_comms.srv import *

"""
  register_foreign_topic.py 
  
  It registers topic that publically available.

  Usage   :
    rosrun rocon_gateway_tests register_foreign_topic.py <topic_name,topic_type,nodeuri> ...
  Example :
    rosrun rocon_gateway_tests register_foreign_service.py /topic1,topic1type,node1uri /topic2,topic2type,node2uri 

    Available public topics can be checked using get_remote_list.py 
    It drops registration if it tries to register local topic
"""
if __name__ == '__main__':

  rospy.init_node('register_public_topic')

  s = rospy.ServiceProxy('/gateway/request',PublicHandler)
  
  if len(sys.argv) < 2:
    print "Usage : rosrun rocon_gateway_tests register_foreign_topic.py \"<topic name>,<topic type>,<node xml uri>\"..."
    sys.exit()

  # all arguements are service info strings
  l = sys.argv[1:len(sys.argv)]
  print "Topics " + str(l)

  # Form a request message
  req = PublicHandlerRequest() 
  req.command = "register_foreign_topic"
  req.list = l

  # Receive whether it is successful
  resp = s(req)

  # Print result
  print resp

