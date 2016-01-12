#!/usr/bin/env python
#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

import os
import socket
import httplib
import errno
import xmlrpclib
from rosmaster.util import xmlrpcapi

import rocon_python_comms

try:
    import urllib.parse as urlparse  # Python 3.x
except ImportError:
    import urlparse
import re

import rospy
import rosgraph
import rostopic
import rosservice
import roslib.names
import gateway_msgs.msg as gateway_msgs

from . import utils, GatewayError
from rocon_python_comms import ConnectionCacheProxy


class LocalMaster(rosgraph.Master):

    '''
      Representing a ros master (local ros master). Just contains a
      few utility methods for retrieving master related information as well
      as handles for registering and unregistering rules that have
      been pulled or flipped in from another gateway.
    '''

    def __init__(self):
        rosgraph.Master.__init__(self, rospy.get_name())
        self._connection_cache = ConnectionCacheProxy(
                list_sub='~connections_list',
                diff_opt=True,
                diff_sub='~connections_diff'
        )

    ##########################################################################
    # Registration
    ##########################################################################

    def register(self, registration):
        '''
          Registers a rule with the local master.

          @param registration : registration details
          @type utils.Registration

          @return the updated registration object (only adds an anonymously generated local node name)
          @rtype utils.Registration
        '''
        # rograph.Master doesn't care whether the node is prefixed with slash or not, but we use it to
        # compare registrations later in FlippedInterface._is_registration_in_remote_rule()
        registration.local_node = "/" + self._get_anonymous_node_name(registration.connection.rule.node)
        rospy.logdebug("Gateway : registering a new node [%s] for [%s]" % (registration.local_node, registration))

        # Then do we need checkIfIsLocal? Needs lots of parsing time, and the outer class should
        # already have handle that.

        node_master = rosgraph.Master(registration.local_node)
        if registration.connection.rule.type == rocon_python_comms.PUBLISHER:
            node_master.registerPublisher(
                registration.connection.rule.name,
                registration.connection.type_info,
                registration.connection.xmlrpc_uri)
            return registration
        elif registration.connection.rule.type == rocon_python_comms.SUBSCRIBER:
            self._register_subscriber(
                node_master,
                registration.connection.rule.name,
                registration.connection.type_info,
                registration.connection.xmlrpc_uri)
            return registration
        elif registration.connection.rule.type == rocon_python_comms.SERVICE:
            node_name = rosservice.get_service_node(registration.connection.rule.name)
            if node_name is not None:
                rospy.logwarn(
                    "Gateway : tried to register a service that is already locally available, aborting [%s][%s]" %
                    (registration.connection.rule.name, node_name))
                return None
            else:
                if registration.connection.rule.name is None:
                    rospy.logerr(
                        "Gateway : tried to register a service with name set to None [%s, %s, %s]" %
                        (registration.connection.rule.name,
                         registration.connection.type_info,
                         registration.connection.xmlrpc_uri))
                    return None
                if registration.connection.type_info is None:
                    rospy.logerr(
                        "Gateway : tried to register a service with type_info set to None [%s, %s, %s]" %
                        (registration.connection.rule.name,
                         registration.connection.type_info,
                         registration.connection.xmlrpc_uri))
                    return None
                if registration.connection.xmlrpc_uri is None:
                    rospy.logerr(
                        "Gateway : tried to register a service with xmlrpc_uri set to None [%s, %s, %s]" %
                        (registration.connection.rule.name,
                         registration.connection.type_info,
                         registration.connection.xmlrpc_uri))
                    return None
                try:
                    node_master.registerService(
                        registration.connection.rule.name,
                        registration.connection.type_info,
                        registration.connection.xmlrpc_uri)
                except rosgraph.masterapi.Error as e:
                    rospy.logerr("Gateway : got error trying to register a service on the local master [%s][%s]" % (
                        registration.connection.rule.name, str(e)))
                    return None
                except rosgraph.masterapi.Failure as e:
                    rospy.logerr("Gateway : failed to register a service on the local master [%s][%s]" % (
                        registration.connection.rule.name, str(e)))
                    return None
                return registration
        elif registration.connection.rule.type == rocon_python_comms.ACTION_SERVER:
            # Need to update these with self._register_subscriber
            self._register_subscriber(
                node_master,
                registration.connection.rule.name +
                "/goal",
                registration.connection.type_info +
                "ActionGoal",
                registration.connection.xmlrpc_uri)
            self._register_subscriber(
                node_master,
                registration.connection.rule.name +
                "/cancel",
                "actionlib_msgs/GoalID",
                registration.connection.xmlrpc_uri)
            node_master.registerPublisher(
                registration.connection.rule.name +
                "/status",
                "actionlib_msgs/GoalStatusArray",
                registration.connection.xmlrpc_uri)
            node_master.registerPublisher(
                registration.connection.rule.name +
                "/feedback",
                registration.connection.type_info +
                "ActionFeedback",
                registration.connection.xmlrpc_uri)
            node_master.registerPublisher(
                registration.connection.rule.name +
                "/result",
                registration.connection.type_info +
                "ActionResult",
                registration.connection.xmlrpc_uri)
            return registration
        elif registration.connection.rule.type == rocon_python_comms.ACTION_CLIENT:
            node_master.registerPublisher(
                registration.connection.rule.name +
                "/goal",
                registration.connection.type_info +
                "ActionGoal",
                registration.connection.xmlrpc_uri)
            node_master.registerPublisher(
                registration.connection.rule.name +
                "/cancel",
                "actionlib_msgs/GoalID",
                registration.connection.xmlrpc_uri)
            self._register_subscriber(node_master, registration.connection.rule.name +
                                      "/status", "actionlib_msgs/GoalStatusArray", registration.connection.xmlrpc_uri)
            self._register_subscriber(
                node_master,
                registration.connection.rule.name +
                "/feedback",
                registration.connection.type_info +
                "ActionFeedback",
                registration.connection.xmlrpc_uri)
            self._register_subscriber(
                node_master,
                registration.connection.rule.name +
                "/result",
                registration.connection.type_info +
                "ActionResult",
                registration.connection.xmlrpc_uri)
            return registration
        return None

    def unregister(self, registration):
        '''
          Unregisters a rule with the local master.

          @param registration : registration details for an existing gateway registered rule
          @type utils.Registration
        '''
        node_master = rosgraph.Master(registration.local_node)
        rospy.logdebug("Gateway : unregistering local node [%s] for [%s]" % (registration.local_node, registration))
        if registration.connection.rule.type == rocon_python_comms.PUBLISHER:
            node_master.unregisterPublisher(registration.connection.rule.name, registration.connection.xmlrpc_uri)
        elif registration.connection.rule.type == rocon_python_comms.SUBSCRIBER:
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name)
        elif registration.connection.rule.type == rocon_python_comms.SERVICE:
            node_master.unregisterService(registration.connection.rule.name, registration.connection.type_info)
        elif registration.connection.rule.type == rocon_python_comms.ACTION_SERVER:
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name + "/goal")
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name + "/cancel")
            node_master.unregisterPublisher(
                registration.connection.rule.name + "/status", registration.connection.xmlrpc_uri)
            node_master.unregisterPublisher(
                registration.connection.rule.name + "/feedback", registration.connection.xmlrpc_uri)
            node_master.unregisterPublisher(
                registration.connection.rule.name + "/result", registration.connection.xmlrpc_uri)
        elif registration.connection.rule.type == rocon_python_comms.ACTION_CLIENT:
            node_master.unregisterPublisher(
                registration.connection.rule.name + "/goal", registration.connection.xmlrpc_uri)
            node_master.unregisterPublisher(
                registration.connection.rule.name + "/cancel", registration.connection.xmlrpc_uri)
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name + "/status")
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name + "/feedback")
            self._unregister_subscriber(
                node_master, registration.connection.xmlrpc_uri, registration.connection.rule.name + "/result")

    def _register_subscriber(self, node_master, name, type_info, xmlrpc_uri):
        '''
          This one is not necessary, since you can pretty much guarantee the
          existence of the subscriber here, but it pays to be safe - we've seen
          some errors come out here when the ROS_MASTER_URI was only set to
          localhost.

          @param node_master : node-master xmlrpc method handler
          @param type_info : type of the subscriber message
          @param xmlrpc_uri : the uri of the node (xmlrpc server)
          @type string
          @param name : fully resolved subscriber name
        '''
        # This unfortunately is a game breaker - it destroys all connections, not just those
        # connected to this master, see #125.
        pub_uri_list = node_master.registerSubscriber(name, type_info, xmlrpc_uri)
        # Be nice to the subscriber, inform it that is should refresh it's publisher list.
        try:
            # rospy.loginfo("register_subscriber [%s][%s][%s]" % (name, xmlrpc_uri, pub_uri_list))
            xmlrpcapi(xmlrpc_uri).publisherUpdate('/master', name, pub_uri_list)
        except socket.error as v:
            errorcode = v[0]
            if errorcode != errno.ECONNREFUSED:
                rospy.logerr(
                    "Gateway : error registering subscriber " +
                    "(is ROS_MASTER_URI and ROS_HOSTNAME or ROS_IP correctly set?)")
                rospy.logerr("Gateway : errorcode [%s] xmlrpc_uri [%s]" % (str(errorcode), xmlrpc_uri))
                raise  # better handling here would be ideal
            else:
                pass  # subscriber stopped on the other side, don't worry about telling it to 'refresh' its publishers
        except xmlrpclib.Fault as e:
            # as above with the socket error, don't worry about telling it to 'refresh' its publishers
            rospy.logerr("Gateway : serious fault while communicating with a subscriber - it's xmlrpc server was around but in a bad state [%s]" % str(e))
            rospy.logerr("Gateway : if this happened, add to the collected information gathered at https://github.com/robotics-in-concert/rocon_multimaster/issues/304")

    def _unregister_subscriber(self, node_master, xmlrpc_uri, name):
        '''
          It is a special case as it requires xmlrpc handling to inform the subscriber of
          the disappearance of publishers it was connected to. It also needs to handle the
          case when that information doesn't get to the subscriber because it is down.

          @param node_master : node-master xmlrpc method handler
          @param xmlrpc_uri : the uri of the node (xmlrpc server)
          @type string
          @param name : fully resolved subscriber name
        '''
        # This unfortunately is a game breaker - it destroys all connections, not just those
        # connected to this master, see #125.
        try:
            xmlrpcapi(xmlrpc_uri).publisherUpdate('/master', name, [])
        except socket.error as v:
            errorcode = v[0]
            if errorcode != errno.ECONNREFUSED:
                raise  # better handling here would be ideal
            else:
                pass  # subscriber stopped on the other side, don't worry about it
        except xmlrpclib.Fault:
            # This occurs when the subscriber has gone down and unflipped.
            # For us this is not an error since we were only informing
            # the subscriber of an updated publisher state...which
            # it no longer needs!
            pass
        except httplib.CannotSendRequest:
            # This occurs if the master has shut down, just ignore this gracefully.
            # I'm not aware that it's important to catch this at any othe time.
            pass
        node_master.unregisterSubscriber(name, xmlrpc_uri)

    ##########################################################################
    # Master utility methods
    ##########################################################################

    def generate_connection_details(self, connection_type, name, node):
        '''
        Creates all the extra details to create a connection object from a
        rule.

        @param connection_type : the connection type (one of gateway_msgs.msg.ConnectionType)
        @type string
        @param name : the name of the connection
        @type string
        @param node : the master node name it comes from
        @param string

        @return the utils.Connection object complete with type_info and xmlrpc_uri
        @type utils.Connection
        '''
        # Very important here to check for the results of xmlrpc_uri and especially topic_type
        #     https://github.com/robotics-in-concert/rocon_multimaster/issues/173
        # In the watcher thread, we get the local connection index (whereby the arguments of this function
        # come from) via master.get_connection_state. That means there is a small amount of time from
        # getting the topic name, to checking for hte xmlrpc_uri and especially topic_type here in which
        # the topic could have disappeared. When this happens, it returns None.
        connections = []
        xmlrpc_uri = node.split(",")[1]
        node = node.split(",")[0]

        if xmlrpc_uri is None:
            return connections
        if connection_type == rocon_python_comms.PUBLISHER or connection_type == rocon_python_comms.SUBSCRIBER:
            type_info = rostopic.get_topic_type(name)[0]  # message type
            if type_info is not None:
                connections.append(utils.Connection(gateway_msgs.Rule(connection_type, name, node), type_info, xmlrpc_uri))
            else:
                rospy.logwarn('Gateway : [%s] does not have type_info. Cannot flip' % name)
        elif connection_type == rocon_python_comms.SERVICE:
            type_info = rosservice.get_service_uri(name)
            if type_info is not None:
                connections.append(utils.Connection(gateway_msgs.Rule(connection_type, name, node), type_info, xmlrpc_uri))
        elif connection_type == rocon_python_comms.ACTION_SERVER:
            goal_type_info = rostopic.get_topic_type(name + '/goal')[0]  # message type
            cancel_type_info = rostopic.get_topic_type(name + '/cancel')[0]  # message type
            status_type_info = rostopic.get_topic_type(name + '/status')[0]  # message type
            feedback_type_info = rostopic.get_topic_type(name + '/feedback')[0]  # message type
            result_type_info = rostopic.get_topic_type(name + '/result')[0]  # message type
            if (
                goal_type_info is not None and cancel_type_info is not None and
                status_type_info is not None and feedback_type_info is not None and
                result_type_info is not None
            ):
                connections.append(utils.Connection(gateway_msgs.Rule(rocon_python_comms.SUBSCRIBER, name + '/goal', node), goal_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.SUBSCRIBER, name + '/cancel', node), cancel_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.PUBLISHER, name + '/status', node), status_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.PUBLISHER, name + '/feedback', node), feedback_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.PUBLISHER, name + '/result', node), result_type_info, xmlrpc_uri))
        elif connection_type == rocon_python_comms.ACTION_CLIENT:
            goal_type_info = rostopic.get_topic_type(name + '/goal')[0]  # message type
            cancel_type_info = rostopic.get_topic_type(name + '/cancel')[0]  # message type
            status_type_info = rostopic.get_topic_type(name + '/status')[0]  # message type
            feedback_type_info = rostopic.get_topic_type(name + '/feedback')[0]  # message type
            result_type_info = rostopic.get_topic_type(name + '/result')[0]  # message type
            if (
                goal_type_info is not None and cancel_type_info is not None and
                status_type_info is not None and feedback_type_info is not None and
                result_type_info is not None
            ):
                connections.append(utils.Connection(gateway_msgs.Rule(rocon_python_comms.PUBLISHER, name + '/goal', node), goal_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.PUBLISHER, name + '/cancel', node), cancel_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.SUBSCRIBER, name + '/status', node), status_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.SUBSCRIBER, name + '/feedback', node), feedback_type_info, xmlrpc_uri))
                connections.append(
                    utils.Connection(gateway_msgs.Rule(rocon_python_comms.SUBSCRIBER, name + '/result', node), result_type_info, xmlrpc_uri))
        return connections

    def generate_advertisement_connection_details(self, connection_type, name, node):
        '''
        Creates all the extra details to create a connection object from an
        advertisement rule. This is a bit different to the previous one - we just need
        the type and single node uri that everything originates from (don't need to generate all
        the pub/sub connections themselves.

        Probably flips could be merged into this sometime, but it'd be a bit gnarly.

        @param connection_type : the connection type (one of gateway_msgs.msg.ConnectionType)
        @type string
        @param name : the name of the connection
        @type string
        @param node : the master node name it comes from
        @param string

        @return the utils.Connection object complete with type_info and xmlrpc_uri
        @type utils.Connection
        '''
        # Very important here to check for the results of xmlrpc_uri and especially topic_type
        #     https://github.com/robotics-in-concert/rocon_multimaster/issues/173
        # In the watcher thread, we get the local connection index (whereby the arguments of this function
        # come from) via master.get_connection_state. That means there is a small amount of time from
        # getting the topic name, to checking for hte xmlrpc_uri and especially topic_type here in which
        # the topic could have disappeared. When this happens, it returns None.
        connection = None
        xmlrpc_uri = self.lookupNode(node)
        if xmlrpc_uri is None:
            return connection
        if connection_type == rocon_python_comms.PUBLISHER or connection_type == rocon_python_comms.SUBSCRIBER:
            type_info = rostopic.get_topic_type(name)[0]  # message type
            if type_info is not None:
                connection = utils.Connection(gateway_msgs.Rule(connection_type, name, node), type_info, xmlrpc_uri)
        elif connection_type == rocon_python_comms.SERVICE:
            type_info = rosservice.get_service_uri(name)
            if type_info is not None:
                connection = utils.Connection(gateway_msgs.Rule(connection_type, name, node), type_info, xmlrpc_uri)
        elif connection_type == rocon_python_comms.ACTION_SERVER or connection_type == rocon_python_comms.ACTION_CLIENT:
            goal_topic = name + '/goal'
            goal_topic_type = rostopic.get_topic_type(goal_topic)
            type_info = re.sub('ActionGoal$', '', goal_topic_type[0])  # Base type for action
            if type_info is not None:
                connection = utils.Connection(gateway_msgs.Rule(connection_type, name, node), type_info, xmlrpc_uri)
        return connection

    def get_ros_ip(self):
        o = urlparse.urlparse(rosgraph.get_master_uri())
        if o.hostname == 'localhost':
            ros_ip = ''
            try:
                ros_ip = os.environ['ROS_IP']
            except Exception:
                try:
                    # often people use this one instead
                    ros_ip = os.environ['ROS_HOSTNAME']
                except Exception:
                    # should probably check other means here - e.g. first of the system ipconfig
                    rospy.logwarn("Gateway : no valid ip found for this host, just setting 'localhost'")
                    return 'localhost'
            return ros_ip
        else:
            return o.hostname

    @staticmethod
    def _is_topic_node_in_list(topic, node, topic_node_list):
        # TODO : there is probably a oneliner equivalent for this
        # check if cancel available
        available = False
        for candidate in topic_node_list:
            if candidate[0] == topic and node in candidate[1]:
                available = True
                break
        return available

    @staticmethod
    def _get_actions(pubs, subs):
        '''
          Return actions and pruned publisher, subscriber lists.

          @param publishers
          @type list of publishers in the form returned by rosgraph.Master.get_system_state
          @param subscribers
          @type list of subscribers in the form returned by rosgraph.Master.get_system_state
          @return list of actions, pruned_publishers, pruned_subscribers
          @rtype [base_topic, [nodes]], as param type, as param type
        '''

        actions = []
        for goal_candidate in pubs:
            if re.search('\/goal$', goal_candidate[0]):
                # goal found, extract base topic
                base_topic = re.sub('\/goal$', '', goal_candidate[0])
                nodes = goal_candidate[1]
                action_nodes = []

                # there may be multiple nodes -- for each node search for the other topics
                for node in nodes:
                    is_action = True
                    is_action &= LocalMaster._is_topic_node_in_list(base_topic + '/goal', node, pubs)
                    is_action &= LocalMaster._is_topic_node_in_list(base_topic + '/cancel', node, pubs)
                    is_action &= LocalMaster._is_topic_node_in_list(base_topic + '/status', node, subs)
                    is_action &= LocalMaster._is_topic_node_in_list(base_topic + '/feedback', node, subs)
                    is_action &= LocalMaster._is_topic_node_in_list(base_topic + '/result', node, subs)

                    if is_action:
                        action_nodes.append(node)

                if len(action_nodes) != 0:
                    # yay! an action has been found
                    actions.append([base_topic, action_nodes])
                    # remove action entries from publishers/subscribers
                    for connection in pubs:
                        if connection[0] in [base_topic + '/goal', base_topic + '/cancel']:
                            for node in action_nodes:
                                try:
                                    connection[1].remove(node)
                                except ValueError:
                                    rospy.logerr(
                                        "Gateway : couldn't remove an action publisher " +
                                        "from the master connections list [%s][%s]" %
                                        (connection[0], node))
                    for connection in subs:
                        if connection[0] in [base_topic + '/status', base_topic + '/feedback', base_topic + '/result']:
                            for node in action_nodes:
                                try:
                                    connection[1].remove(node)
                                except ValueError:
                                    rospy.logerr(
                                        "Gateway : couldn't remove an action subscriber " +
                                        "from the master connections list [%s][%s]" %
                                        (connection[0], node))
        pubs[:] = [connection for connection in pubs if len(connection[1]) != 0]
        subs[:] = [connection for connection in subs if len(connection[1]) != 0]
        return actions, pubs, subs

    @staticmethod
    def _get_action_servers(publishers, subscribers):
        '''
          Return action servers and pruned publisher, subscriber lists.

          @param publishers
          @type list of publishers in the form returned by rosgraph.Master.get_system_state
          @param subscribers
          @type list of subscribers in the form returned by rosgraph.Master.get_system_state
          @return list of actions, pruned_publishers, pruned_subscribers
          @rtype [base_topic, [nodes]], as param type, as param type
        '''
        actions, subs, pubs = LocalMaster._get_actions(subscribers, publishers)
        return actions, pubs, subs

    @staticmethod
    def _get_action_clients(publishers, subscribers):
        """
          Return action clients and pruned publisher, subscriber lists.

          @param publishers
          @type list of publishers in the form returned by rosgraph.Master.get_system_state
          @param subscribers
          @type list of subscribers in the form returned by rosgraph.Master.get_system_state
          @return list of actions, pruned_publishers, pruned_subscribers
          @rtype [base_topic, [nodes]], as param type, as param type
        """
        actions, pubs, subs = LocalMaster._get_actions(publishers, subscribers)
        return actions, pubs, subs

    def get_connection_state(self):

        try:
            publishers, subscribers, services, = self._connection_cache.getSystemState(silent_fallback=False)
            pubs, subs, action_servers, action_clients = self._connection_cache.filterActions(publishers, subscribers)
            topic_types = self._connection_cache.getTopicTypes(silent_fallback=False)

            service_uris = self._connection_cache.getServiceUris()
        except rocon_python_comms.UnknownSystemState:
            raise GatewayError("System State not received from Connection Cache Node. Aborting.")

        connections = utils.create_empty_connection_type_dictionary()
        connections[gateway_msgs.ConnectionType.ACTION_SERVER] = utils._get_connections_from_action_list(action_servers, gateway_msgs.ConnectionType.ACTION_SERVER, topic_types)
        connections[gateway_msgs.ConnectionType.ACTION_CLIENT] = utils._get_connections_from_action_list(action_clients, gateway_msgs.ConnectionType.ACTION_CLIENT, topic_types)
        connections[gateway_msgs.ConnectionType.PUBLISHER] = utils._get_connections_from_pub_sub_list(pubs, gateway_msgs.ConnectionType.PUBLISHER, topic_types)
        connections[gateway_msgs.ConnectionType.SUBSCRIBER] = utils._get_connections_from_pub_sub_list(subs, gateway_msgs.ConnectionType.SUBSCRIBER, topic_types)
        connections[gateway_msgs.ConnectionType.SERVICE] = utils._get_connections_from_service_list(services, gateway_msgs.ConnectionType.SERVICE, service_uris)

        return connections

    @staticmethod
    def _get_anonymous_node_name(topic):
        t = topic[1:len(topic)]
        name = roslib.names.anonymous_name(t)
        return name
