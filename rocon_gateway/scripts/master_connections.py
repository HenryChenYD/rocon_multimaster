#!/usr/bin/env python
#       
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/rocon_gateway/LICENSE 
#

##############################################################################
# Imports
##############################################################################

import sys
import rocon_gateway

class Flags(object):
    advertise = 'advertise'
    cancel = 'cancel'

##############################################################################
# Functions
##############################################################################
    

##############################################################################
# Main
##############################################################################

if __name__ == '__main__':
    
    rospy.init_node('master_connections')
    master = rocon_gateway.LocalMaster()
    publishers, subscribers, services = master.getSystemState()
    print("Publishers; \n%s" % publishers)
    print("Publishers; \n%s" % subscribers)
