#!/usr/bin/env pythonupdate
#       
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/multimaster_client/rocon_gateway/LICENSE 
#

import redis
import threading
import roslib; roslib.load_manifest('rocon_gateway')
import rospy
import re
import utils

###############################################################################
# Utility Functions
###############################################################################

def createKey(key):
    '''
      Root the specified redis key name in our pseudo redis database.
    '''
    if re.match('rocon:',key): # checks if leading rocon: is foundupdate
        return key
    else:
        return 'rocon:'+key

def extractKey(key):
    '''
      Extract the specified redis key name from our pseudo redis database.
    '''
    if re.match('rocon:',key): # checks if leading rocon: is found
        return re.sub(r'rocon:','',key)
    else:
        return key

def keyBaseName(key):
    '''
      Extract the base name (i.e. last value) from the key.
      e.g. rocon:key:pirate24 -> pirate24
    '''
    return key.split(':')[-1]

def resolveHub(ip, port):
    '''
      Pings the hub for identification. We currently use this to check
      against the gateway whitelist/blacklists to determine if a rule
      should proceed or not.
      
      @return string - hub name
    '''
    r = redis.Redis()
    return r.get("rocon:hub:name") # perhaps should store all key names somewhere central

###############################################################################
# Redis Callback Handler
##############################################################################

class RedisListenerThread(threading.Thread):
    '''
      Tunes into the redis channels that have been subscribed to and
      calls the apropriate callbacks.
    '''
    def __init__(self,redis_pubsub_server,remote_gateway_request_callbacks):
        threading.Thread.__init__(self)
        self.redis_pubsub_server = redis_pubsub_server
        self.remote_gateway_request_callbacks = remote_gateway_request_callbacks
            
    def run(self):
        '''
          Used as a callback for incoming requests on redis pubsub channels.
          
          The received argument is a list of strings for 'flip':
          
            - [0] - command : this one is 'flip'
            - [1] - remote_gateway : the name of the gateway that is flipping to us
            - [2] - remote_name 
            - [3] - remote_node
            - [4] - type : one of ConnectionType.PUBLISHER etc
            - [5] - type_info : a ros format type (e.g. std_msgs/String or service api)
            - [6] - xmlrpc_uri : the xmlrpc node uri
            
          The command 'unflip' is the same, not including args 5 and 6.
            
        '''
        for r in self.redis_pubsub_server.listen():
            if r['type'] != 'unsubscribe' and r['type'] != 'subscribe':
                command, source, contents = utils.deserializeRequest(r['data'])
                rospy.logdebug("Gateway : redis listener received a channel publication from %s : [%s]"%(source,command))
                if command == 'flip':
                    registration = utils.Registration(utils.getConnectionFromList(contents), source)
                    self.remote_gateway_request_callbacks['flip'](registration)
                elif command == 'unflip':
                    self.remote_gateway_request_callbacks['unflip'](utils.getRuleFromList(contents), source)
                else:
                    rospy.logerr("Gateway : received an unknown command from the hub.")

##############################################################################
# Hub Manager - Redis Implementation
##############################################################################

class Hub(object):

    pool = None
    server = None
    pubsub = None
    callback = None

    def __init__(self,remote_gateway_request_callbacks,gateway_name):
        self.name = '' # the hub name
        self._gateway_name = gateway_name # used to generate the unique name key later
        self.remote_gateway_request_callbacks = remote_gateway_request_callbacks
        self.redis_keys = {}
        #self.redis_keys['name'] = '' # it's a unique id generated later when connecting
        self.redis_keys['index'] = createKey('hub:index') # used for uniquely id'ing the gateway (client)
        self.redis_keys['gatewaylist'] = createKey('gatewaylist')
        self.redis_channels = {}
        self.redis_channels['update_topic'] = createKey('update')
        self.redis_pubsub_server = None
        
    ##########################################################################
    # Hub
    ##########################################################################

    def connect(self,ip,portarg):
        try:
            self.pool = redis.ConnectionPool(host=ip,port=portarg,db=0)
            self.server = redis.Redis(connection_pool=self.pool)
            rospy.logdebug("Gateway : connected to the hub's redis server.")
            self.redis_pubsub_server = self.server.pubsub()
        except redis.exceptions.ConnectionError as e:
            rospy.logerror("Gateway : failed rule to the hub's redis server.")
            raise

    def listGateways(self):
        '''
          Return a list of the gateways (name list, not redis keys).
          e.g. ['gateway32','pirate33']
        '''
        gateway_keys = self.server.smembers(self.redis_keys['gatewaylist']) 
        gateway_list = []
        for gateway in gateway_keys:
            gateway_list.append(keyBaseName(gateway))
        return gateway_list

    def listPublicInterfaces(self, gateways = None):
        '''
          Return all the 'remote' public interfaces connnected to the hub.
        '''
        public_interfaces = {}
        if gateways == None:
            gateways = self.listGateways()
        for gateway in gateways:
            gateway_key = createKey(gateway)
            key = gateway_key +":connection"
            public_interface = self.server.smembers(key)
            public_interfaces[gateway] = []
            for connection_str in public_interface:
                connection = utils.deserializeConnection(connection_str)
                public_interfaces[gateway].append(connection.rule) 
        return public_interfaces

    def getRemoteConnectionState(self, gateway):
        '''
          Equivalent to getConnectionState, but generates it from the public
          interface of a foreign gateway
       '''
        connections = utils.createEmptyConnectionTypeDictionary()
        gateway_key = createKey(gateway)
        key = gateway_key +":connection"
        public_interface = self.server.smembers(key)
        for connection_str in public_interface:
            connection = utils.deserializeConnection(connection_str)
            connections[connection.rule.type].append(connection)
        return connections
        
    ##########################################################################
    # Gateway Rule
    ##########################################################################

    def registerGateway(self):
        '''
          Register a gateway with the hub. Note that you must have already
          connected before calling this function.
          
          On registration, the hub will provide a unique identifier number
          which will be appended to the suggested name of this gateway to 
          ensure a unique id string and key for this gateway.
          
          @return: success or failure of the operation
          @rtype: bool
          
          @todo - maybe merge with 'connect', or at the least check if it
          is actually connected here first.
        '''
        unique_num = self.server.incr(self.redis_keys['index'])
        self.redis_keys['name'] = createKey(self._gateway_name+str(unique_num))
        self.server.sadd(self.redis_keys['gatewaylist'],self.redis_keys['name'])
        self.redis_pubsub_server.subscribe(self.redis_channels['update_topic'])
        self.redis_pubsub_server.subscribe(self.redis_keys['name'])
        self.remote_gateway_listener_thread = RedisListenerThread(self.redis_pubsub_server, self.remote_gateway_request_callbacks)
        self.remote_gateway_listener_thread.start()
        self.name = keyBaseName(self.server.get("rocon:hub:name"))
        return keyBaseName(self.redis_keys['name'])

    def unregisterGateway(self):
        '''
          Remove all gateway info from the hub.
          
          @return: success or failure of the operation
          @rtype: bool
        '''
        try:
            pipe = self.server.pipeline()
            public_interface_list = self.redis_keys['name'] +":rule"
            pipe.delete(public_interface_list)
            pipe.srem(self.redis_keys['gatewaylist'],self.redis_keys['name'])
            pipe.execute()
            self.redis_pubsub_server.unsubscribe()
            self.name = ''
        except Exception as e:
            rospy.logerr("Gateway : error unregistering gateway from the hub (need better error handling here).")
            return False
        rospy.loginfo("Gateway : unregistering gateway from the hub.")
        return True

    ##########################################################################
    # Public Interface
    ##########################################################################

    def advertise(self, connection):
        '''
          Places a topic, service or action on the public interface. On the
          redis server, this representation will always be:
          
           - topic : a triple { name, type, xmlrpc node uri }
           - service : a triple { name, rosrpc uri, xmlrpc node uri }
           - action : ???
           
          @param connection: representation of a connection (topic, service, action)
          @type  connection: str
          @raise .exceptions.ConnectionTypeError: if connectionarg is invalid.
        '''
        key = self.redis_keys['name']+":connection"
        msg_str = utils.serializeConnection(connection)
        self.server.sadd(key,msg_str)
    
    def unadvertise(self, connection):
        '''
          Removes a topic, service or action from the public interface.
          
          @param connection: representation of a connection (topic, service, action)
          @type  connection: str
          @raise .exceptions.ConnectionTypeError: if connectionarg is invalid.
        '''
        key = self.redis_keys['name']+":connection"
        msg_str = utils.serializeConnection(connection)
        self.server.srem(key,msg_str)

    ##########################################################################
    # Gateway-Gateway Communications
    ##########################################################################

    def broadcastTopicUpdate(self,msg):
        self.server.publish(self.redis_channels['update_topic'],msg)

    ##########################################################################
    # Messages to Remote Gateways (via redis publisher channels)
    ##########################################################################
    
    def sendFlipRequest(self, gateway, connection):
        '''
          Sends a message to the remote gateway via redis pubsub channel. This is called from the 
          watcher thread, when a flip rule gets activated.

           - redis channel name: rocon:<remote_gateway_name>
           - data : list of [ command, gateway, rule type, type, xmlrpc_uri ]
            - [0] - command       : in this case 'flip'
            - [1] - gateway       : the name of this gateway, i.e. the flipper
            - [2] - name          : local name  
            - [3] - node          : local node name
            - [4] - connection_type : one of ConnectionType.PUBLISHER etc
            - [5] - type_info     : a ros format type (e.g. std_msgs/String or service api)
            - [6] - xmlrpc_uri    : the xmlrpc node uri
            
          @param command : string command name - either 'flip' or 'unflip'
          @type str
          
          @param flip_rule : the flip to send
          @type RemoteRule
          
          @param type_info : topic type (e.g. std_msgs/String)
          @param str
          
          @param xmlrpc_uri : the node uri
          @param str
        '''
        source = keyBaseName(self.redis_keys['name'])
        cmd = utils.serializeConnectionRequest('flip', source, connection)
        try:
            self.server.publish(createKey(gateway),cmd)
        except Exception as e:
            return False
        return True

    def sendUnflipRequest(self, gateway, rule):
        source = keyBaseName(self.redis_keys['name'])
        cmd = utils.serializeRuleRequest('unflip', source, rule)
        try:
            self.server.publish(createKey(gateway),cmd)
        except Exception as e:
            return False
        return True

    ##########################################################################
    # Depracating
    ##########################################################################

    # DJS need to get rid of these, no point in piping if you are only
    # sending one command at a time.
    
#    def addMembers(self,key,topic):
#        try:
#            pipe = self.server.pipeline()
#            pipe.sadd(key,topic)
#            pipe.execute()
#        except:
#            print "Error : addMembers"
#            return False
#        return True
#
#    def removeMembers(self,key,string):
#        try:
#            pipe = self.server.pipeline()
#            pipe.srem(key,string)
#            pipe.execute()
#        except:
#            print "Error : removeMembers"
#            return False
#        return True

#    def listPublicInterfaces(self):
#        '''
#          Return all the 'remote' public interfaces connnected to the hub.
#        '''
#        public_interfaces = {}
#        gateway_keys = self.server.smembers(self.redis_keys['gatewaylist'])
#        for gateway_key in gateway_keys:
#            gateway = keyBbaseName(gateway_key)
#            public_interfaces[gateway] = {}
#            # get public topic list of this master
#            key = gateway_key +":topic"
#            public_interfaces[gateway]['topic'] = self.server.smembers(key)
#
#            # get public service list of this master
#            key = gateway_key +":service"
#            public_interfaces[gateway]['service'] = self.server.smembers(key)
#        return public_interfaces
