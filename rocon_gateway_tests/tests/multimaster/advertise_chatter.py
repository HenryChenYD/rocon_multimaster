#!/usr/bin/env python
#       
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/rocon_gateway_tests/LICENSE 
#

import roslib; roslib.load_manifest('rocon_gateway_tests')
import rospy
import rocon_gateway
import rocon_gateway_tests
from gateway_comms.msg import *
from gateway_comms.srv import *
import argparse
import sys

"""
  Tests a single advertise rule.
  
  Usage:
    1 > roslaunch rocon_gateway_hub pirate.launch
    2a> roslaunch rocon_gateway pirate_chatter.launch
    3a> roslaunch rocon_gateway pirate.launch
    3b> rosrun rocon_gateway_tests advertise_chatter.py
    3c> rosservice call /gateway/gateway_info[]
    2b> rosservice call /gateway/remote_gateway_info []
"""

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Flip /chatter to a remote gateway')
    parser.add_argument('--cancel', action='store_true', help='cancel the flip')
    args = parser.parse_args()
 
    rospy.init_node('advertise_chatter')

    try:
        gateway = rocon_gateway_tests.findFirstRemoteGateway()
    except rocon_gateway.GatewayError as e:
        rospy.logerr("Flip Test : %s, aborting."%(str(e)))
        sys.exit(1)

    gateway_info = rospy.ServiceProxy('/gateway/gateway_info',GatewayInfo)
    advertise = rospy.ServiceProxy('/gateway/advertise',Advertise)
  
  
    req = AdvertiseRequest()
    req.rules = []
    public_rule = Rule()
    public_rule.name = "/chatter"
    public_rule.type = gateway_comms.msg.ConnectionType.PUBLISHER
    public_rule.node = "/talker"
    req.rules.append(public_rule)
    req.cancel = args.cancel
    
    print ""
    print "== Request =="
    print ""
    print req
    print ""
    resp = advertise(req)
    print "== Response =="
    print ""
    print resp
    
    gateway_info_request = GatewayInfoRequest()
    gateway_info_response = gateway_info(gateway_info_request)
    print ""
    print "== Gateway Info =="
    print ""
    print gateway_info_response
    print ""
