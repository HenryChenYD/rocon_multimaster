#!/usr/bin/env python
#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_multimaster/license/LICENSE
#

##############################################################################
# Imports
##############################################################################

##############################################################################
# Exceptions
##############################################################################


class TimeoutExpiredError(Exception):
    pass


class ResourceNotFoundException(IOError):
    """
      Resource Not Found Exception
    """
    pass


class ServiceNotFoundException(IOError):
    """
      Raised when a service with service type cannot be found.
    """
    pass


class InvalidPlatformTuple(Exception):
    pass
