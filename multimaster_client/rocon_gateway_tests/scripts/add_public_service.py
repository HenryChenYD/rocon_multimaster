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
#    * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#    * Neither the name of Yujin Robot nor the names of its
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
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
from rocon_gateway_helper import *
from gateway_comms.msg import *
from gateway_comms.srv import *

"""
    add_public_service.py 
    
    It publicize local service to the centralised multimaster server

    Usage     :
        rosrun rocon_gateway_tests add_public_service.py <service_name,service_api,node uri> ...
    Example :
        rosrun rocon_gateway_tests add_public_service.py /add_two_ints,<service_api>,<nodeuri>

        Lookup    local service : 
            rosservice list
"""

if __name__ == '__main__':

    rospy.init_node('add_public_service')

    s = rospy.ServiceProxy('/gateway/request',PublicHandler)
    
    if len(sys.argv) < 2:
        print "Usage : rosrun rocon_gateway_tests add_public_service.py <service name,service api,node uri> ..."
        sys.exit()
    
    # all arguements are service names
    l = sys.argv[1:len(sys.argv)]
    print "Service " + str(l)

    """
    ll = []
    for srv in l:
        sname,suri,nuri = get_service_info(srv)
        info = sname + "," + suri + "," + nuri
        ll.append(info)
    """

    # Form a request message
    req = PublicHandlerRequest() 
    req.command = "add_public_service"
    req.list = l

    # Receive whether it is successful
    resp = s(req)

    # Print result
    print resp

