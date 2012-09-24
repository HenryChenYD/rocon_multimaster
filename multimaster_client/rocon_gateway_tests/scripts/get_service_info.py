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
import rosservice
import rosnode
import rosgraph
import sys
import argparse

"""
  get_service_info.py

  It prints general service information including 
    service name, service uri, and service node uri

  Usage : 
    rosrun rocon_gateway_tests get_service_info.py --service <service_name>
    rosrun rocon_gateway_tests get_service_info.py --service /add_two_ints
"""

if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Provides a Service information and triple.')
  parser.add_argument('-s','--service',metavar='<Service name>',type=str,help='Ex : /add_two_ints')
  args = parser.parse_args()

  rospy.init_node('get_service_info')
  name = rospy.get_name()
  master = rosgraph.Master(name)

  try:
    service_name = args.service
    srvuri = rosservice.get_service_uri(service_name) 
    nodename = rosservice.get_service_node(service_name)
    nodeuri = rosnode.get_api_uri(master,nodename)

    print "== Service =="
    print " - Name     : " + service_name
    print " - Uri      : " + srvuri
    print " - Node Uri : " + nodeuri

    info = service_name + "," + srvuri + "," + nodeuri
    print " - Concat   : " + info

  except Exception as e:
    print str(e)


