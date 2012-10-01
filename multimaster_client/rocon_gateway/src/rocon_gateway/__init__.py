#!/usr/bin/env python
#       
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/master/multimaster_client/rocon_gateway/LICENSE 
# Copyright (c) 2012, Yujin Robot, Daniel Stonier
#

__author__ = "Daniel Stonier, Jihoon Lee"
__copyright__ = "Copyright (c) 2012 Daniel Stonier, Yujin Robot"
__license__ = "BSD"
__version__ = '0.1.0'
__date__ = "2012-08-29"

from .hub import resolveHub
from .zeroconf import resolveZeroconfAddress
