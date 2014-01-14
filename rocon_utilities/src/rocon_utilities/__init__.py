#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/rocon_utilities/LICENSE
#
##############################################################################
# Imports
##############################################################################

from launch import main as launch, parse_rocon_launcher
from gateways import create_gateway_remote_rule, create_gateway_rule, gateway_basename
import ros_utilities as ros
from ros_utilities import (
        find_resource,
        find_resource_from_string,
        package_index_from_package_path
        )
from exceptions import TimeoutExpiredError
from icons import icon_to_msg, icon_resource_to_msg
from system import Popen
from pinger import Pinger
import platform_info

##############################################################################
# Deprecating Messages
##############################################################################
# SubscriberProxy and console has moved, but bring it in here to support current code
# and notify users of a new repository.
try:
    from rocon_python_comms import SubscriberProxy
    from rocon_python_comms import WallRate
    from rocon_console import console
except ImportError:
    import sys
    print("Error: some functionality has shifted - please make sure [rocon_tools](https://github.com/robotics-in-concert/rocon_tools) is in your workspace.")
    sys.exit(1)
