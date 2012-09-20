#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Yujin Robot, Daniel Stonier , Jihoon Lee
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#  copyright notice, this list of conditions and the following
#  disclaimer in the documentation and/or other materials provided
#  with the distribution.
#  * Neither the name of Yujin Robot nor the names of its
#  contributors may be used to endorse or promote products derived
#  from this software without specific prior written permission.
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

import os
import sys
import time
import ConfigParser
import argparse

try:
    import redis
except ImportError:
    sys.exit("\n[ERROR] No python-redis found - hint 'rosdep install rocon_gateway_hub'\n")

##############################################################################
# Logging
##############################################################################

is_ros_environment = False

def loginfo(message):
    if is_ros_environment:
        rospy.loginfo(message)
    else:
        print("[ INFO] "+message+"\n")
        
##############################################################################
# Ros
##############################################################################

is_ros_environment = False

try:
    import roslib; roslib.load_manifest('rocon_gateway_hub')
    import rospy
    import rosgraph
    is_ros_environment = True
    loginfo("Ros modules imported")
except ImportError:
    loginfo("No ros environment detected.")

##############################################################################
# Option Parser
##############################################################################

def parse_options():
    
    parser = argparse.ArgumentParser(description="\
        Starts the ros multimaster hub:\n\n\
  1. Launches a central redis server for gateway information and interactions\n\
  2. Optionally advertises a zeroconf service appropriate to your platform",
        epilog="See http://www.ros.org/wiki/rocon_multimaster for details.",
        formatter_class=argparse.RawTextHelpFormatter )
    parser.add_argument('-z', '--zeroconf', action='store_false',  # default is true
                        help='publish the hub on zeroconf [true]')
    parser.add_argument('-n', '--name', action='store',
                   default='Gateway Hub',
                   help='string identifier for this hub [Gateway Hub]')
    return parser.parse_args()
    
##############################################################################
# Config Parser
##############################################################################

def parse_config(filename):

    f = open(filename,'r')
    settings = {}

    for line in f:
        kv = line.split()
        if len(kv) > 1:
            settings[kv[0]]= kv[1]
    return settings

##############################################################################
# Check Package availability
##############################################################################

def check_if_package_available(package_name):

    import subprocess
    devnull = open(os.devnull,"w")
    retval = subprocess.call(["dpkg","-s",package_name],stdout=devnull,stderr=subprocess.STDOUT)
    devnull.close()

    if retval != 0:
        sys.exit("\n[ERROR] " + package_name + " not installed - hint 'rosdep install rocon_gateway_hub'\n")

##############################################################################
# Initialize redis server 
##############################################################################

def initialize_redis_server(p):
    pool = redis.ConnectionPool(host='localhost', port=p, db=0)
    server = redis.Redis(connection_pool=pool)

    pipe = server.pipeline()
    # Don't flush other programs use of the hub.
    pipe.flushall()
    pipe.set("index",0)
    pipe.execute()
    print "Clean up all database. set \"index\" 0"


##############################################################################
# avahi advertisement
##############################################################################

def advertise_port_to_avahi(config):
    port = config["port"]
    os.system('avahi-publish -s ros-gateway-hub _ros-gateway-hub._tcp '+str(port))
    loginfo(("advertising _ros-gateway-hub._tcp on port "+str(port)))


##############################################################################
# Main
##############################################################################

if __name__ == '__main__':    


    if is_ros_environment:
        try:
            rospy.init_node('hub')
            zeroconf_flag = rospy.get_param("~zeroconf",True)
            hub_name = rospy.get_param("~name","Gateway Hub")
            loginfo("ros initialised.")
        except NameError:
            sys.exit("[ERROR] ros environment detected, but failed to initialise.")
    else:
        args = parse_options()
        hub_name = args.name
        zeroconf_flag = args.zeroconf

    # These abort if not found 
    check_if_package_available('redis-server')
    check_if_package_available('avahi-daemon')

    # check if the daemons (redis and avahi) are running by testing
    # their connection and functionality explicitly    


  # flush all the previous data. and set unique key for indexing clients
    config = parse_config('/etc/redis/redis.conf')
    initialize_redis_server(int(config["port"]))

  # Try to autodetect the system and start redis appropriately
  # Try to autodetect the system and start zeroconf appropriately
  # Linux
  # TODO: If port is zero, find a free port here before advertising
  # Might need to track this one so we can kill it when the program 
  # terminates
    advertise_port_to_avahi(config)

    if is_ros_environment:
        rospy.spin()
    
