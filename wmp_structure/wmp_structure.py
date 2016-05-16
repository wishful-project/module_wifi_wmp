__author__ = 'domenico'

# Generic API to control the lower layers, i.e. key-value configuration.

class execution_engine_t:
    """
    The information elements used by the UPI_R interface are organized into data structures, which provide information
    on a specific execution environment. This class representing the data structure that contains the execution
    environment information.
    """

    execution_engine_id = ""
    """ Identifier of the execution environment """

    execution_engine_name = ""
    """ Name of the execution environment """

    supported_platform = ""
    """ Platform of the execution environment """

    execution_engine_pointer = ""
    """ Path of the execution environment """

class radio_program_t:
    """
    The information elements used by the UPI_R interface are organized into data structures, which provide information
    on a specific radio program. This class representing the data structure that contains the radio program
    information.
    """

    radio_prg_id = ""
    """ Identifier of the radio program """

    radio_prg_name = ""
    """ Name of the radio program """

    supported_platform = ""
    """ Platform of the radio program """

    radio_prg_pointer = ""
    """ Path of the radio program """

class radio_platform_t(object):
	"""
	The information elements used by the UPI_R interface are organized into data structures, which provide information
	on the platform type of each interface,over the radio interface.
	This class representing the data structure information of a radio interface, it contains an identifier and the
	platform type.
	"""
	def __init__(self,platform_id="",platform_type=""):
		self.platform_id = platform_id
		""" interface identifier or interface name """
		self.platform_type = platform_type
		""" platform interface """
		pass

	def __str__(self):
		return ""+self.platform_id+","+self.platform_type

class radio_info_t:
    """
    The information elements used by the UPI_R interface are organized into data structures, which provide information
    on radio capabilities (monitor_t, param_t) of each interface (RadioPlatform_t) on the available radio programs (radio_prg_t),
    over the radio interface.
    This class representing the radio capabilities of a given network card RadioPlatform_t in terms of measurement list,
    parameters lists, execution environment list and radio program list.

    """
    platform_info = None
    """ Interface information structured such as RadioPlatform_t object """

    monitor_list = []
    """ The list of supported measurements """

    param_list = []
    """ The list of supported parameters """

    radio_program_list = None
    """ The list of supported radio program """

    execution_engine_list = None
    """ The list of supported execution environment """


    # get/set rf channel on a wireless network interface
#    IEEE80211_CHANNEL = "IEEE80211_CHANNEL"

