import logging
import random
import pickle
import os
import inspect
import subprocess
import zmq
import time
import platform
import numpy as np
import iptc
import csv
import shutil


from pytc.TrafficControl import TrafficControl


import wishful_module_wifi
import wishful_upis as upis

from agent_modules.wifi_wmp.wmp_structure import execution_engine_t
from agent_modules.wifi_wmp.wmp_structure import radio_platform_t
from agent_modules.wifi_wmp.wmp_structure import radio_info_t
from agent_modules.wifi_wmp.wmp_structure import radio_program_t
from agent_modules.wifi_wmp.wmp_structure import UPI_R
from agent_modules.wifi_wmp.adaptation_module.libb43 import *

import wishful_framework as wishful_module
from wishful_framework.classes import exceptions
#import wishful_framework.upi_arg_classes.edca as edca #<----!!!!! Important to include it here; otherwise cannot be pickled!!!!
#import wishful_framework.upi_arg_classes.flow_id as FlowId


__author__ = "Domenico Garlisi"
__copyright__ = "Copyright (c) 2015, Technische Universität Berlin"
__version__ = "0.1.0"
__email__ = "{gomenico.garlisi@cnit.it"

# Used by local controller for communication with mac processor
LOCAL_MAC_PROCESSOR_CTRL_PORT = 1217




""" Store the current radio program information for WMP """
class memory_slot_info_t:

    radio_program_name = ''
    """ The radio program name"""

    radio_program_pointer = ''
    """ The radio program pointer """



""" Store the current radio program information for WMP """
class WMP_info_t:
    platform_info = "WMP"
    """ platform specification"""

    interface_id = "wlan0"

    memory_slot_number = 2
    """ number of memory slot for the platform """

    memory_slot_active = 1
    """ the memory slot active """

    memory_slot_list = []



@wishful_module.build_module
class WmpModule(wishful_module_wifi.WifiModule):
    def __init__(self):
        super(WmpModule, self).__init__()
        self.log = logging.getLogger('WmpModule')
        self.channel = 1
        self.power = 1

        self.SUCCESS = 0
        self.PARTIAL_SUCCESS = 1
        self.FAILURE = 2

        #global b43_phy
        self.b43_phy = None
        global NIC_list
        global radio_info
        self.WMP_status = WMP_info_t()
        self.WMP_status.memory_slot_list = [memory_slot_info_t() for i in range(self.WMP_status.memory_slot_number)]

    """
    UPI_M implementation
    """

    """
    UPI_M implementation
    """

    @wishful_module.bind_function(upis.radio.install_execution_engine)
    def install_execution_engine(self, myargs):
        execution_engine_value = None
        module_value = None
        execution_engine_value = myargs['execution_engine']
        execution_engine_value = execution_engine_value[0]

        self.log.warning('install_execution_engine(): %s' % (str(execution_engine_value)))

        dst = ""
        module_dst = "/lib/modules/3.13.11-ckt19-custom/kernel/drivers/net/wireless/b43/"
        microcode_dst = "/lib/firmware/b43/"

        #self.log.debug('copy file on : %s' % key[ii])
        if execution_engine_value != None:
            dst = microcode_dst
            path_1 = execution_engine_value + '/ucode5.fw'
            path_2 = execution_engine_value + '/b0g0initvals5.fw'
            path_3 = execution_engine_value + '/b0g0bsinitvals5.fw'
            try:
                #self.log.debug('copy file path_1 : %s on dest : %s' % (path_1, dst) )
                shutil.copy(path_1, dst)
                shutil.copy(path_2, dst)
                shutil.copy(path_3, dst)
            except Exception as e:
                self.log.debug('Unable to copy file. %s' % e)
                return False

        if module_value != None:
            dst = module_dst
            path_1 = module_value + '/b43.ko'
            try:
                shutil.copy(path_1, dst)
            except Exception as e:
                self.log.debug('Unable to copy file. %s' % e)
                return False

        return True

    @wishful_module.bind_function(upis.radio.init_test)
    def init_test(self, myargs):
        import subprocess
        self.log.warning('initTest(): %s' % str(myargs) )
        key = myargs['operation']
        interface = myargs['interface']
        try:
            for ii in range(0,len(key)):
                self.log.debug('key: %s' % str(key[ii]) )

                if key[ii] == "module":
                    cmd_str = 'lsmod | grep b43 | wc -l'
                    cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    time.sleep(1)
                    if (int(cmd_output)>0):
                        cmd_str = 'rmmod b43'
                        cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    time.sleep(1)
                    cmd_str = 'modprobe b43 qos=0 && sleep 0.5 && ifconfig wlan0 up'
                    cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    self.log.debug('cmd_output: %s' % cmd_output)

                if key[ii] == "association":
                    value_1 = myargs['ssid']
                    value_2 = myargs['ip_address']
                    cmd_str = '../../agent_modules/wifi_wmpx/network_script/association.sh ' + value_1[ii] + ' ' +value_2[ii]
                    subprocess.call(cmd_str, shell=True)
                    self.log.info('------------------------------ end STA association ------------------------')

                if key[ii] == "monitor":
                    value_1 = myargs['channel']
                    cmd_str = '../../agent_modules/wifi_wmp/network_script/setup_monitor.sh ' + value_1[ii]
                    subprocess.call(cmd_str, shell=True)
                    self.log.info('------------------------------ end STA monitor ------------------------')

                if key[ii] == "create-network":
                    value_1 = myargs['ssid']
                    value_2 = myargs['ip_address']

                    cmd_str = 'cat ../../agent_modules/wifi_wmp/network_script/hostapd2_start.conf > ./runtime/connectors/wmp_linux/network_script/hostapd2.conf'
                    #self.log.debug('cmd_str: %s' % cmd_str)
                    subprocess.Popen(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    time.sleep(1)
                    cmd_str = 'echo ssid=' + value_1[ii] + ' >>  ./runtime/connectors/wmp_linux/network_script/hostapd2.conf '
                    #self.log.debug('cmd_str: %s' % cmd_str)

                    subprocess.Popen(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    time.sleep(1)
                    cmd_str = '../../agent_modules/wifi_wmp/network_script/create_network.sh '  + value_2[ii]
                    #self.log.debug('cmd_str: %s' % cmd_str)

                    subprocess.Popen(cmd_str, shell=True, stderr=subprocess.STDOUT)
                    self.log.info('------------------------------ end AP CONFIGURATION ------------------------')

        except B43Exception as e:
            self.log.debug('initTest raised an exception:  %s' % e)

        return True


    """
    UPI_R implementation
    """
    @wishful_module.bind_function(upis.radio.get_radio_platforms)
    def get_radio_platforms(self):
        self.log.warning('get_radio_platforms()')

        cmd_str = 'lsmod | grep b43 | wc -l'
        cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
        time.sleep(1)
        if (int(cmd_output)==0):
            cmd_str = 'modprobe b43 qos=0'
            cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
        time.sleep(1)
        #self.log.debug('output %s', command)

        command = "../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager --get-interface-name"
        nl_output = ""

        try:
            nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        except: # catch *all* exceptions
            self.log.debug('Error on subprocess call %s', nl_output)

        nl_output = nl_output.decode('ascii')
        self.log.debug('command output %s', str(nl_output))
        flow_info_lines = nl_output.rstrip().split('\n')
        NIC_list = [radio_platform_t() for i in range(len(flow_info_lines))]

        for ii in range(len(flow_info_lines)):
            tmp = flow_info_lines[ii]
            items = tmp.split(",")
            NIC_list[ii].platform_info = items[0]
            NIC_list[ii].platform = items[1]

        NIC_list_string = [NIC_list[ii].platform_info, NIC_list[ii].platform]
        self.log.debug('NIC_list_string %s', str(NIC_list_string))
        return NIC_list_string

    @wishful_module.bind_function(upis.radio.get_radio_info)
    def get_radio_info(self, interface):
        radio_id = interface
        platform = "WMP"
        self.log.warning('get_radio_info(): %s : %s' % ( str(radio_id), str(platform) ) )

        radio_info = radio_info_t()
        radio_info.platform_info = radio_platform_t()

        radio_info.platform_info.platform_id = radio_id
        radio_info.platform_info.platform = platform

        #get available engines
        exec_engine_current_list_name = []
        exec_engine_current_list_pointer = []
        with open('../../agent_modules/wifi_wmp/wmp_repository/execution_engine_repository.csv') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                #filter for WMP platform
                #self.log.debug(" %s " %  str(row['execution_engine_name']) )
                exec_engine_current_list_name.append(row['execution_engine_name'])
                exec_engine_current_list_pointer.append(row['execution_engine_pointer'])
            radio_info.execution_engine_list = [execution_engine_t() for i in range(len(exec_engine_current_list_name))]
            for ii in range(len(exec_engine_current_list_name)):
                radio_info.execution_engine_list[ii].execution_engine_name = exec_engine_current_list_name[ii]
                radio_info.execution_engine_list[ii].execution_engine_pointer = exec_engine_current_list_pointer[ii]
                #self.log.debug(" execution engine %s " %  radio_info.execution_engine_list[ii].execution_engine_pointer )


        #get available repository
        radio_prg_current_list_name = []
        radio_prg_current_list_pointer = []
        with open('../../agent_modules/wifi_wmp/wmp_repository/radio_program_repository.csv') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                #filter for WMP platform
                #self.log.debug(" radio prg name : %s " %  str(row['radio_prg_name']) )
                radio_prg_current_list_name.append(row['radio_prg_name'])
                radio_prg_current_list_pointer.append(row['radio_prg_pointer'])
            radio_info.radio_program_list = [radio_program_t() for i in range(len(radio_prg_current_list_name))]
            for ii in range(len(radio_prg_current_list_name)):
                radio_info.radio_program_list[ii].radio_prg_name = radio_prg_current_list_name[ii]
                radio_info.radio_program_list[ii].radio_prg_pointer = radio_prg_current_list_pointer[ii]

        b43 = B43(self.b43_phy)
        radio_info.monitor_list = b43.monitor_list
        radio_info.param_list = b43.param_list
        ret_lst = []
        ret_lst = {'radio_info' : [radio_info.platform_info.platform_id, radio_info.platform_info.platform],
                   'event_list' : [''], 'monitor_list' : [b43.monitor_list], 'param_list' : [b43.param_list],
                   'radio_prg_list_name' : [radio_prg_current_list_name], 'radio_prg_list_pointer' : [radio_prg_current_list_pointer],
                   'exec_engine_list_name' : [exec_engine_current_list_name], 'exec_engine_list_pointer' : [exec_engine_current_list_pointer],
                   }
        #execution_engine_list = None
        self.log.debug("ret_lst %s " %  ret_lst )
        return ret_lst

    @wishful_module.bind_function(upis.radio.get_parameter_lower_layer)
    def get_parameter_lower_layer(self, myargs):
        self.log.warning('get_parameter_lower_layer(): %s' % str(myargs))
        ret_lst = []

        # if myargs.has_key('cmd'):
        #     cmd = myargs['cmd']
        #     if cmd == UPI_R.NETWORK_INTERFACE_HW_ADDRESS:
        #         return self.getHwAddr(myargs)
        #     elif cmd == UPI_R.IEEE80211_L2_BCAST_TRANSMIT_RATE:
        #         return self.genBacklogged80211L2BcastTraffic(myargs)
        #     elif cmd == UPI_R.IEEE80211_L2_GEN_LINK_PROBING:
        #         return self.gen80211L2LinkProbing(myargs)
        #     elif cmd == UPI_R.IEEE80211_L2_SNIFF_LINK_PROBING:
        #         return self.sniff80211L2LinkProbing(myargs)
        #     else:
        #         self.log.error('getParameterLowerLayer(): unknown parameter with command (cmd)')

        if 'parameters' in myargs:
            key_parameter = myargs['parameters']
            for ii in range(0,len(key_parameter)):
                if key_parameter[ii] == UPI_R.CSMA_CW:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.CSMA_CW) )
                elif key_parameter[ii] == UPI_R.CSMA_CW_MIN:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.CSMA_CW_MIN) )
                elif key_parameter[ii] == UPI_R.CSMA_CW_MAX:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.CSMA_CW_MAX) )
                elif key_parameter[ii] == UPI_R.TDMA_SUPER_FRAME_SIZE:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.TDMA_SUPER_FRAME_SIZE) )
                elif key_parameter[ii] == UPI_R.TDMA_NUMBER_OF_SYNC_SLOT:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.TDMA_NUMBER_OF_SYNC_SLOT) )
                elif key_parameter[ii] == UPI_R.TDMA_ALLOCATED_SLOT:
                    ret_lst.append( self.readRadioProgramParameters(UPI_R.TDMA_ALLOCATED_SLOT) )
                else:
                    self.log.error('get_parameter_lower_layer(): unknown parameter with parameters (parameters)')

        self.log.debug('get_parameter_lower_layer() exit : %s' % str(ret_lst))
        return ret_lst

    # def defineEvent(self, myargs):
    #     raise ValueError('Not yet implemented')
    #

    @wishful_module.bind_function(upis.radio.set_parameter_lower_layer)
    def set_parameter_lower_layer(self, myargs):
        self.log.warning('setParameterLowerLayer(): %s' % (str(myargs)))
        ret_lst = []

        #manage TDMA slot parameter
        super_frame_size = 0
        number_of_sync_slot = 0
        if UPI_R.TDMA_SUPER_FRAME_SIZE in myargs:
            super_frame_size = myargs[UPI_R.TDMA_SUPER_FRAME_SIZE]
        if UPI_R.TDMA_NUMBER_OF_SYNC_SLOT in myargs:
            number_of_sync_slot = myargs[UPI_R.TDMA_NUMBER_OF_SYNC_SLOT]
        if super_frame_size != 0 or number_of_sync_slot !=0 :
            if super_frame_size != 0 and number_of_sync_slot != 0 :
                self.log.debug('setting superframe and number_of_sync_slot slot')
                slot_duration = super_frame_size /  number_of_sync_slot
                ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_SUPER_FRAME_SIZE, slot_duration ) )
                ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_NUMBER_OF_SYNC_SLOT, number_of_sync_slot ) )
            if super_frame_size == 0 and number_of_sync_slot != 0 :
                self.log.debug('setting number_of_sync_slot slot')
                slot_duration = self.readRadioProgramParameters(UPI_R.TDMA_SUPER_FRAME_SIZE)
                old_number_of_allocated_slot = self.readRadioProgramParameters(UPI_R.TDMA_NUMBER_OF_SYNC_SLOT)
                slot_duration = (slot_duration * old_number_of_allocated_slot) /  number_of_sync_slot
                ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_SUPER_FRAME_SIZE, slot_duration ) )
                ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_NUMBER_OF_SYNC_SLOT, number_of_sync_slot ) )
            if super_frame_size != 0 and number_of_sync_slot == 0 :
                self.log.debug('setting superframe')
                number_of_sync_slot = self.readRadioProgramParameters(UPI_R.TDMA_NUMBER_OF_SYNC_SLOT)
                slot_duration = super_frame_size /  number_of_sync_slot
                ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_SUPER_FRAME_SIZE, slot_duration ) )
            self.startBootStrapOperation()


        #manage other parameter
        # if  UPI_R.IEEE80211_CHANNEL in myargs:
        #     ret_lst.append( self.setRfChannel(myargs) )
        # if  UPI_R.IEEE80211_CONNECT_TO_AP in myargs:
        #     ret_lst.append( self.connectToAP(myargs) )
        if  UPI_R.CSMA_CW in myargs:
            ret_lst.append( self.setRadioProgramParameters(UPI_R.CSMA_CW, myargs[UPI_R.CSMA_CW]) )
        if  UPI_R.CSMA_CW_MIN in myargs:
            ret_lst.append( self.setRadioProgramParameters(UPI_R.CSMA_CW_MIN, myargs[UPI_R.CSMA_CW_MIN]) )
        if  UPI_R.CSMA_CW_MAX in myargs:
            ret_lst.append( self.setRadioProgramParameters(UPI_R.CSMA_CW_MAX, myargs[UPI_R.CSMA_CW_MAX]) )
        if  UPI_R.TDMA_ALLOCATED_SLOT in myargs:
            ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_ALLOCATED_SLOT, myargs[UPI_R.TDMA_ALLOCATED_SLOT] ) )
        if  UPI_R.TDMA_ALLOCATED_MASK_SLOT in myargs:
            ret_lst.append( self.setRadioProgramParameters(UPI_R.TDMA_ALLOCATED_MASK_SLOT, myargs[UPI_R.TDMA_ALLOCATED_MASK_SLOT] ) )
        if  UPI_R.MAC_ADDR_SYNCHRONIZATION_AP in myargs:
                mac_address_end = myargs[UPI_R.MAC_ADDR_SYNCHRONIZATION_AP]
                self.log.debug('ADDRESS 1: %s' % mac_address_end)
                mac_address_end = mac_address_end.replace(':', '')
                self.log.debug('ADDRESS 2: %s' % mac_address_end)
                mac_address_end = mac_address_end[-2:] + mac_address_end[-4:-2]
                self.log.debug('ADDRESS 3: %s' % mac_address_end)
                int_mac_address_end = int(mac_address_end, 16)
                ret_lst.append( self.setRadioProgramParameters(UPI_R.MAC_ADDR_SYNCHRONIZATION_AP, int_mac_address_end ) )

        return ret_lst

    @wishful_module.bind_function(upis.radio.get_active)
    def get_active(self, myargs):
        self.log.warning('get_active(): ')
        interface = myargs['interface']
        command = '../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager -v'
        nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        nl_output = nl_output.decode('ascii')
        flow_info_lines = nl_output.rstrip().split('\n')
        items = flow_info_lines[1].split(" ")
        active_radio_program = items[4]
        self.log.debug('active_radio_program : %s' % str(active_radio_program))
        return active_radio_program

    """ we join this function with set active """
    # def inject(self,  interface, radioProgramName, param_key_value):
    #     import subprocess
    #     self.log.debug('inject(): %s ' %  str(param_key_value))
    #     radio_program_path = ''
    #     position = None
    #
    #     radio_program_path = param_key_value['PATH']
    #     position = param_key_value['POSITION']
    #
    #     if position == None :
    #         position = 1
    #
    #     command = '../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager -l ' + position + ' -m ' + radio_program_path
    #     #self.log.debug('output %s ', command)
    #
    #     nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    #     self.log.debug('output %s ', nl_output)
    #
    #     flow_info_lines = nl_output.rstrip().split('\n')
    #     #items = flow_info_lines[1].split(" ")
    #     if flow_info_lines[5] == 'end load file' :
    #         self.log.debug('Radio program successfully injected!')
    #         return True
    #     else :
    #         self.log.debug('Radio program inject error')
    #         return False

    @wishful_module.bind_function(upis.radio.set_active)
    def set_active(self,  myargs):
        position = None
        radio_program_path = ''
        radio_program_name = ''
        self.log.warning('set_active(): %s ' %  str(myargs))

        if 'position' in myargs:
            if (myargs['position'] == '1'):
                position = 1
            elif (myargs['position'] == '2'):
                position = 2
            else :
                return self.FAILURE

        if 'radio_program_name' in myargs:
            radio_program_name = myargs['radio_program_name']
        if 'path' in myargs:
            radio_program_path = myargs['path']

        #get the current radio program injected
        #injected_radio_program = getInjectedRadioProgram()

        #identification the operation
        # 1 = activation by position
        # 2 = activation by name
        # 3 = activation by position and name
        # 4 = injection + activation by position
        # 5 = injection + activation by name
        # 6 = injection + activation by position and name
        if radio_program_path == '' :
            if position == None and radio_program_name == '':
                return self.FAILURE

            elif position != None and radio_program_name == '':
                operation = 1

            elif position == None and radio_program_name != '':
                for i in range(self.WMP_status.memory_slot_number):
                    if self.WMP_status.memory_slot_list[i].radio_program_name == radio_program_name :
                        position = i+1

                if position == None :
                    return self.FAILURE
                else :
                    operation = 2

            else :
                operation = 3

        else :
            if position == None and radio_program_name == '':
                return self.FAILURE

            elif position != None and radio_program_name == '':
                operation = 4
                radio_program_name = "NO-NAME"

            elif position == None and radio_program_name != '':
                for i in range(self.WMP_status.memory_slot_number):
                    if self.WMP_status.memory_slot_list[i].radio_program_name == radio_program_name :
                        position = i+1

                    if position == None :
                        if self.WMP_status.memory_slot_active == 1 :
                            position = 2
                        else :
                            position = 1

                    operation = 5

            else:
                operation = 6

        """ radio program injection on WMP platform """
        #handled only if operation number is great of 3
        self.log.debug('operation : %d - radio_program_name = %s - position = %d - radio_program_path = %s' %  (operation, radio_program_name, position, radio_program_path) )
        if operation > 3 :
            command = '../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager -l ' + str(position) + ' -m ' + radio_program_path
            nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            nl_output = nl_output.decode('ascii')
            self.log.debug(' bytecode-manager command result : %s' % nl_output)
            flow_info_lines = nl_output.rstrip().split('\n')
            if not(flow_info_lines[5] == 'end load file') :
                return self.FAILURE
            else :
                self.WMP_status.memory_slot_list[(position-1)].radio_program_name = radio_program_name
                self.WMP_status.memory_slot_list[(position-1)].radio_program_pointer = radio_program_path

        """ radio program activation """
        command = '../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager -a ' + str(position)
        nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        nl_output = nl_output.decode('ascii')
        self.log.debug(' bytecode-manager command result : %s' % nl_output)
        flow_info_lines = nl_output.rstrip().split('\n')
        if (position == 1 and flow_info_lines[0] == 'Active byte-code 1') or (position == 2 and flow_info_lines[0] == 'Active byte-code 2') :
            self.WMP_status.memory_slot_active = position
            return self.SUCCESS
        else :
            return self.FAILURE

    @wishful_module.bind_function(upis.radio.set_inactive)
    def set_inactive(self, myargs):
        """ radio program activation """
        radio_program_name = myargs['radio_program_name']
        command = '../../agent_modules/wifi_wmp/adaptation_module/src/bytecode-manager -d ' + radio_program_name
        nl_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        nl_output = nl_output.decode('ascii')
        flow_info_lines = nl_output.rstrip().split('\n')
        if flow_info_lines[0] == 'InActive byte-code 1' :
            return self.SUCCESS
        elif flow_info_lines[0] == 'InActive byte-code 2' :
            return self.SUCCESS
        else :
            return self.FAILURE


    #******
    #read
    #******
    def readRadioProgramParameters(self, offset_parameter=0):

        b43 = B43(self.b43_phy)
        val = 0
        val_2 = 0

        gpr_byte_code_value = b43.shmRead16(b43.B43_SHM_REGS, b43.BYTECODE_ADDR_OFFSET)
        active_slot=0
        if not (offset_parameter==UPI_R.CSMA_CW or offset_parameter==UPI_R.CSMA_CW_MIN or offset_parameter== UPI_R.CSMA_CW_MAX or offset_parameter == UPI_R.REGISTER_1 or offset_parameter == UPI_R.REGISTER_2):
            if gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_1 :
                active_slot = 1
            elif gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_2 :
                active_slot = 2
            else :
                self.log.error('readRadioProgramParameters(): no active slot')
                return val

        if offset_parameter == UPI_R.CSMA_CW:
            val = b43.shmRead16(b43.B43_SHM_REGS, b43.GPR_CUR_CONTENTION_WIN)
        elif offset_parameter == UPI_R.CSMA_CW_MIN:
            val = b43.shmRead16(b43.B43_SHM_REGS, b43.GPR_MIN_CONTENTION_WIN)
        elif offset_parameter == UPI_R.CSMA_CW_MAX:
            val = b43.shmRead16(b43.B43_SHM_REGS, b43.GPR_MAX_CONTENTION_WIN)
        elif offset_parameter == UPI_R.REGISTER_1:
            val = b43.shmRead16(b43.B43_SHM_REGS, b43.PROCEDURE_REGISTER_1)
        elif offset_parameter == UPI_R.REGISTER_2:
            val = b43.shmRead16(b43.B43_SHM_REGS, b43.PROCEDURE_REGISTER_2)
        elif offset_parameter == UPI_R.TDMA_SUPER_FRAME_SIZE :
            if active_slot == 1 :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_SUPER_FRAME_SIZE)
                val_2 = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_NUMBER_OF_SYNC_SLOT)
            else :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_SUPER_FRAME_SIZE)
                val_2 = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_NUMBER_OF_SYNC_SLOT)

            self.log.error('readRadioProgramParameters(): val %s : val_2 %s' % (str(val), str(val_2)))
            val = val * val_2
        elif offset_parameter == UPI_R.TDMA_NUMBER_OF_SYNC_SLOT :
            if active_slot == 1 :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_NUMBER_OF_SYNC_SLOT)
            else :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_NUMBER_OF_SYNC_SLOT)
        elif offset_parameter == UPI_R.TDMA_ALLOCATED_SLOT :
            if active_slot == 1 :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_ALLOCATED_SLOT)
            else :
                val = b43.shmRead16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_ALLOCATED_SLOT)
        else:
            self.log.error('readRadioProgramParameters(): unknown parameter')

        #self.log.debug('B43 control ret value %d' % val)
        return val

    #******
    #set
    #******
    def setRadioProgramParameters(self, offset_parameter=0, value=0):
        b43 = B43(self.b43_phy)
        write_share = False
        write_gpr = False

        value = int(value)
        self.log.debug('setRadioProgramParameters(): offset = %s - value = %s' % (str(offset_parameter), str(value)))
        gpr_byte_code_value = b43.shmRead16(b43.B43_SHM_REGS, b43.BYTECODE_ADDR_OFFSET);
        active_slot=0

        if  not (offset_parameter==UPI_R.CSMA_CW or offset_parameter==UPI_R.CSMA_CW_MIN or offset_parameter== UPI_R.CSMA_CW_MAX or offset_parameter == UPI_R.REGISTER_1 or offset_parameter == UPI_R.REGISTER_2 or offset_parameter == UPI_R.MAC_ADDR_SYNCHRONIZATION_AP):
            if gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_1 :
                active_slot = 1
                #self.log.debug('detected active slot 1')
            elif gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_2 :
                active_slot = 2
                #self.log.debug('detected active slot 2')
            else :
                self.log.error('readRadioProgramParameters(): no active slot')
                return False

        if offset_parameter == UPI_R.MAC_ADDR_SYNCHRONIZATION_AP:
            offset_parameter_gpr= b43.MAC_ADDR_SYNCHRONIZATION_AP_GPR
            write_gpr = True
        elif offset_parameter == UPI_R.CSMA_CW:
            offset_parameter_share= b43.SHM_EDCFQCUR + b43.SHM_EDCFQ_CWCUR
            offset_parameter_gpr= b43.GPR_CUR_CONTENTION_WIN
            write_share = True
            write_gpr = True
        elif offset_parameter == UPI_R.CSMA_CW_MIN:
            offset_parameter_share= b43.SHM_EDCFQCUR + b43.SHM_EDCFQ_CWMIN
            offset_parameter_gpr= b43.GPR_MIN_CONTENTION_WIN
            write_share = True
            write_gpr = True
        elif offset_parameter == UPI_R.CSMA_CW_MAX:
            offset_parameter_share= b43.SHM_EDCFQCUR + b43.SHM_EDCFQ_CWMAX
            offset_parameter_gpr= b43.GPR_MAX_CONTENTION_WIN
            write_share = True
            write_gpr = True
        elif offset_parameter == UPI_R.REGISTER_1:
            offset_parameter_gpr= b43.PROCEDURE_REGISTER_1
            write_gpr = True
        elif offset_parameter == UPI_R.REGISTER_2:
            offset_parameter_gpr= b43.PROCEDURE_REGISTER_2
            write_gpr = True
        elif offset_parameter == UPI_R.TDMA_SUPER_FRAME_SIZE :
            #self.log.debug('start : write super frame size %d' % value)
            if active_slot == 1 :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_SUPER_FRAME_SIZE, value)
                #self.log.debug('slot 1 : write super frame size %d' % value)
            else :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_SUPER_FRAME_SIZE, value)
                #self.log.debug('slot 2 : write super frame size %d' % value)
        elif offset_parameter == UPI_R.TDMA_NUMBER_OF_SYNC_SLOT:
            if active_slot == 1 :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_NUMBER_OF_SYNC_SLOT, value)
            else :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_NUMBER_OF_SYNC_SLOT, value)
        elif offset_parameter == UPI_R.TDMA_ALLOCATED_SLOT  :
            if active_slot == 1 :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_ALLOCATED_SLOT, value)
            else :
                b43.shmWrite16(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_ALLOCATED_SLOT, value)
        elif offset_parameter == UPI_R.TDMA_ALLOCATED_MASK_SLOT  :
            if active_slot == 1 :
                b43.shmWrite32(b43.B43_SHM_SHARED, b43.SHM_SLOT_1_TDMA_ALLOCATED_MASK_SLOT, value)
            else :
                b43.shmWrite32(b43.B43_SHM_SHARED, b43.SHM_SLOT_2_TDMA_ALLOCATED_MASK_SLOT, value)
        else :
            self.log.error('setRadioProgramParameters(): unknown parameter')
            return self.FAILURE

        if write_share :
            b43.shmWrite16(b43.B43_SHM_SHARED, offset_parameter_share, value)
        if write_gpr :
            b43.shmWrite16(b43.B43_SHM_REGS, offset_parameter_gpr, value)

        return self.SUCCESS

    @wishful_module.bind_function(upis.radio.get_monitor)
    def get_monitor(self, myargs):
        iw_command_monitor = False
        microcode_monitor = False
        key = myargs['measurements']
        interface = myargs['interface']
        self.log.debug('get_monitor(): %s len : %d' % (str(key), len(key)))
        ret_lst = []

        for ii in range(0,len(key)):
            if key[ii] == UPI_R.NUM_TX_SUCCESS:
                iw_command_monitor = True
            if key[ii] == UPI_R.NUM_TX:
                microcode_monitor = True
            if key[ii] == UPI_R.NUM_TX_DATA_FRAME:
                microcode_monitor = True
            if key[ii] == UPI_R.BUSY_TYME:
                microcode_monitor = True
            if key[ii] == UPI_R.NUM_FREEZING_COUNT:
                microcode_monitor = True
            if key[ii] == UPI_R.TX_ACTIVITY:
                microcode_monitor = True
            if key[ii] == UPI_R.NUM_RX:
                microcode_monitor = True
            if key[ii] == UPI_R.NUM_RX_SUCCESS:
                microcode_monitor = True
            if key[ii] == UPI_R.NUM_RX_MATCH:
                microcode_monitor = True
            if key[ii] == UPI_R.TSF:
                microcode_monitor = True
            if key[ii] == UPI_R.REGISTER_1:
                microcode_monitor = True
            if key[ii] == UPI_R.REGISTER_2:
                microcode_monitor = True

        if  microcode_monitor:
            b43 = B43(self.b43_phy)

        if  iw_command_monitor:
            cmd_str = 'iw dev ' + interface + ' station dump'
            #self.log.debug('cmd_str: %s' % cmd_str)
            cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
            cmd_output = cmd_output.decode('ascii')
            #self.log.debug('cmd_output: %s' % cmd_output)
            # parse serialized data and create data structures
            flow_info_lines = cmd_output.rstrip().split('\n')
            #self.log.debug(' row number %d' % len(flow_info_lines))
            if len(flow_info_lines) < 3 :
                self.log.error('getMonitor(): iw command error')
                return False

            for ii in range(len(flow_info_lines)):
                tmp = flow_info_lines[ii]
                #self.log.debug('%d ) getMonitor(): %s' % (ii, tmp))
                items = tmp.split("\t")
                if ii == 3:
                    rx_packet = items[2]
                elif ii == 5:
                    tx_packet = items[2]
                elif ii == 6:
                    tx_retries = items[2]
                elif ii == 7:
                    tx_failed = items[2]
                else:
                    continue
            tx_packet_success = int(tx_packet)
            tx_packet = int(tx_packet) + int(tx_retries) + int(tx_failed)
            if tx_packet_success < 0 :
                tx_packet_success = 0

        for ii in range(0,len(key)):
            if key[ii] == UPI_R.TSF:
                while True :
                        v3 = b43.read16(b43.B43_MMIO_TSF_3)
                        v2 = b43.read16(b43.B43_MMIO_TSF_2)
                        v1 = b43.read16(b43.B43_MMIO_TSF_1)
                        v0 = b43.read16(b43.B43_MMIO_TSF_0)
                        test3 = b43.read16(b43.B43_MMIO_TSF_3)
                        test2 = b43.read16(b43.B43_MMIO_TSF_2)
                        test1 = b43.read16(b43.B43_MMIO_TSF_1)
                        if v3 == test3 and v2 == test2 and v1 == test1 :
                            break
                ret_lst.append( (v3 << 48) + (v2 << 32) + (v1 << 16) + v0 )
            if key[ii] == UPI_R.BUSY_TYME:
                ret_lst.append( b43.shmRead32(b43.B43_SHM_SHARED, b43.BUSY_TIME_CHANNEL) )
                #self.log.debug('getMonitor(): value 1 : %s ' % value_1)
            if key[ii] == UPI_R.NUM_FREEZING_COUNT:
                ret_lst.append( b43.shmRead16(b43.B43_SHM_SHARED, b43.NUM_FREEZING_COUNT) )
                #self.log.debug('getMonitor(): value 1 : %s ' % value_1)
            if key[ii] == UPI_R.TX_ACTIVITY:
                ret_lst.append( b43.shmRead32(b43.B43_SHM_SHARED, b43.TX_ACTIVITY) )
                #self.log.debug('getMonitor(): value 2 : %s ' % value_2)
            if key[ii] == UPI_R.NUM_RX:
                total_receive = b43.shmRead16(b43.B43_SHM_SHARED, b43.BAD_PLCP_COUNTER)             #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.INVALID_MACHEADER_COUNTER)   #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.BAD_FCS_COUNTER)             #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_TOO_LONG_COUNTER)         #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_TOO_SHORT_COUNTER)        #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_CRS_GLITCH_COUNTER)       #trace failure
                total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER)            #trace success
                ret_lst.append(total_receive)
                #self.log.debug('getMonitor(): value num_rx : %s ' % total_receive)
            if key[ii] == UPI_R.NUM_RX_SUCCESS:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER))
                #value_3 = b43.shmRead32(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER)
                #self.log.debug('getMonitor(): value 2 : %s ' % value_3)
            if key[ii] == UPI_R.NUM_RX_MATCH:
                #ret_lst.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_MATCH_RA_COUNTER))
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.GOOD_FCS_MATCH_RA_COUNTER))
                #ret_lst.append(rx_packet)
            if key[ii] == UPI_R.NUM_TX:
               ret_lst.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.TX_COUNTER))
            #   ret_lst.append(tx_packet)
            if key[ii] == UPI_R.NUM_TX_DATA_FRAME:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.TX_DATA_FRAME_COUNTER))
            #    ret_lst.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.TX_DATA_FRAME_COUNTER))
            if key[ii] == UPI_R.NUM_RX_ACK:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.RX_ACK_COUNTER))
            #    ret_lst.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_ACK_COUNTER))
            if key[ii] == UPI_R.NUM_RX_ACK_RAMATCH:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.RX_ACK_COUNTER_RAMATCH))
            if key[ii] == UPI_R.NUM_TX_SUCCESS:
                ret_lst.append(tx_packet_success)
            if key[ii] == UPI_R.REGISTER_1:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.PROCEDURE_REGISTER_1))
            if key[ii] == UPI_R.REGISTER_2:
                ret_lst.append(b43.shmRead16(b43.B43_SHM_REGS, b43.PROCEDURE_REGISTER_2))

        self.log.debug('call result: %s' % ret_lst)
        return ret_lst
#
#
#
#     def getMonitorBounce(self, myargs):
#         import subprocess
#
#         iw_command_monitor = False
#         microcode_monitor = False
#
#         self.log.debug('getMonitorBounce(): %s len : %d' % (str(myargs), len(myargs)))
#         key = myargs['measurements']
#         slot_period = myargs['slot_period']
#         frame_period = myargs['frame_period']
#         interface = myargs['interface']
#         cumulative_reading = []
#         reading = []
#
#         for ii in range(0,len(key)):
#             if key[ii] == UPI_R.NUM_TX:
#                 iw_command_monitor = True
#             if key[ii] == UPI_R.NUM_TX_SUCCESS:
#                 iw_command_monitor = True
#             if key[ii] == UPI_RN.BUSY_TYME:
#                 microcode_monitor = True
#             if key[ii] == UPI_RN.NUM_FREEZING_COUNT:
#                 microcode_monitor = True
#             if key[ii] == UPI_RN.TX_ACTIVITY:
#                 microcode_monitor = True
#             if key[ii] == UPI_R.NUM_RX:
#                 microcode_monitor = True
#             if key[ii] == UPI_RN.NUM_RX_SUCCESS:
#                 microcode_monitor = True
#             if key[ii] == UPI_RN.NUM_RX_MATCH:
#                 microcode_monitor = True
#             if key[ii] == UPI_RN.TSF:
#                 microcode_monitor = True
#
#
#         if  microcode_monitor:
#             b43 = B43(b43_phy)
#
#         num_sampling_total = frame_period / slot_period
#         num_sampling = 0
#         while True :
#
#             if  iw_command_monitor:
#                 cmd_str = 'iw dev ' + interface + ' station dump'
#                 #self.log.debug('cmd_str: %s' % cmd_str)
#                 cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#                 #self.log.debug('cmd_output: %s' % cmd_output)
#                 # parse serialized data and create data structures
#                 flow_info_lines = cmd_output.rstrip().split('\n')
#                 #self.log.debug(' row number %d' % len(flow_info_lines))
#                 if len(flow_info_lines) < 3 :
#                     self.log.error('getMonitorBounce(): iw command error')
#                     return False
#
#                 for ii in range(len(flow_info_lines)):
#                     tmp = flow_info_lines[ii]
#                     #self.log.debug('%d ) getMonitor(): %s' % (ii, tmp))
#                     items = tmp.split("\t")
#                     if ii == 3:
#                         rx_packet = items[2]
#                     elif ii == 5:
#                         tx_packet = items[2]
#                     elif ii == 6:
#                         tx_retries = items[2]
#                     elif ii == 7:
#                         tx_failed = items[2]
#                     else:
#                         continue
#                 tx_packet_success = int(tx_packet)
#                 tx_packet = int(tx_packet) + int(tx_retries) + int(tx_failed)
#
#
#                 if tx_packet_success < 0 :
#                     tx_packet_success = 0
#
#             for ii in range(0,len(key)):
#                 if key[ii] == UPI_RN.TSF:
#                     while True :
#                             v3 = b43.read16(b43.B43_MMIO_TSF_3)
#                             v2 = b43.read16(b43.B43_MMIO_TSF_2)
#                             v1 = b43.read16(b43.B43_MMIO_TSF_1)
#                             v0 = b43.read16(b43.B43_MMIO_TSF_0)
#                             test3 = b43.read16(b43.B43_MMIO_TSF_3)
#                             test2 = b43.read16(b43.B43_MMIO_TSF_2)
#                             test1 = b43.read16(b43.B43_MMIO_TSF_1)
#                             if v3 == test3 and v2 == test2 and v1 == test1 :
#                                 break
#                     reading.append( ((v3 << 48) + (v2 << 32) + (v1 << 16) + v0) )
#                 if key[ii] == UPI_RN.BUSY_TYME:
#                     reading.append( b43.shmRead32(b43.B43_SHM_SHARED, b43.BUSY_TIME_CHANNEL) )
#                     #self.log.debug('getMonitorBounce: BUSY_TIME_CHANNEL : %s ' % reading)
#                 if key[ii] == UPI_RN.NUM_FREEZING_COUNT:
#                     reading.append( b43.shmRead16(b43.B43_SHM_SHARED, b43.NUM_FREEZING_COUNT) )
#                     #self.log.debug('getMonitorBounce: BUSY_TIME_CHANNEL : %s ' % reading)
#                 if key[ii] == UPI_RN.TX_ACTIVITY:
#                     reading.append( b43.shmRead32(b43.B43_SHM_SHARED, b43.TX_ACTIVITY_CHANNEL) )
#                     #self.log.debug('getMonitorBounce(): TX_ACTIVITY_CHANNEL : %s ' % reading)
#                 if key[ii] == UPI_RN.NUM_RX:
#                     total_receive = b43.shmRead16(b43.B43_SHM_SHARED, b43.BAD_PLCP_COUNTER)             #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.INVALID_MACHEADER_COUNTER)   #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.BAD_FCS_COUNTER)             #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_TOO_LONG_COUNTER)         #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_TOO_SHORT_COUNTER)        #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.RX_CRS_GLITCH_COUNTER)       #trace failure
#                     total_receive += b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER)            #trace success
#                     reading.append(total_receive)
#                     #self.log.debug('getMonitor(): value num_rx : %s ' % total_receive)
#                 if key[ii] == UPI_RN.NUM_RX_SUCCESS:
#                     reading.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER))
#                     #value_3 = b43.shmRead32(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER)
#                     #self.log.debug('getMonitor(): value 2 : %s ' % value_3)
#                 if key[ii] == UPI_RN.NUM_RX_MATCH:
#                     reading.append(b43.shmRead16(b43.B43_SHM_SHARED, b43.GOOD_FCS_MATCH_RA_COUNTER))
#                     #value_3 = b43.shmRead32(b43.B43_SHM_SHARED, b43.GOOD_FCS_COUNTER)
#                     #self.log.debug('getMonitor(): value 2 : %s ' % value_3)
#                 if key[ii] == UPI_R.NUM_TX:
#                     reading.append( tx_packet )
#                 if key[ii] == UPI_R.NUM_TX_SUCCESS:
#                     reading.append( tx_packet_success )
#
#             cumulative_reading.append(reading)
#             reading = []
#             num_sampling += 1
#             if num_sampling == num_sampling_total :
#                 #self.log.debug('sampling num %d' % num_sampling)
#                 #self.log.debug('call result: %s' % str(cumulative_reading))
#                 return cumulative_reading
#             time.sleep(slot_period/1000000.0)
#
#         return cumulative_reading
#
#     """ IMPL """
#     def setPerFlowTxPower(self, myargs):
#         import pickle
#         from pytc.TrafficControl import TrafficControl
#
#         self.log.debug('Slave: setPerFlowTxPower')
#         self.log.debug('margs = %s' % str(myargs))
#
#         ifname = myargs["interface"]
#         flowDesc = pickle.loads(myargs["flowDesc"])
#         txPower = myargs["txPower"]
#
#         tcMgr = TrafficControl()
#         markId = tcMgr.generateMark()
#         myargs["markId"] = markId
#         myargs["table"] = "mangle"
#         myargs["chain"] = "POSTROUTING"
#         self.setMarking(myargs)
#
#         cmd_str = ('sudo iw ' + ifname + ' info')
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         for item in cmd_output.split("\n"):
#              if "wiphy" in item:
#                 line = item.strip()
#
#         phyId = [int(s) for s in line.split() if s.isdigit()][0]
#
#         try:
#             myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'w')
#         except Exception as e:
#             self.log.fatal("Operation not supported: %s" % e)
#             msg = {"ReturnValue": "ERROR"}
#             return msg
#
#         value = str(markId) + " " + str(txPower) + " 0"
#         myfile.write(value)
#         myfile.close()
#
#         msg = {"ReturnValue": "OK"}
#         return msg
#
    """
    Manage operation
    """
    def startBootStrapOperation(self):
        b43 = B43(self.b43_phy)
        gpr_byte_code_value = b43.shmRead16(b43.B43_SHM_REGS, b43.BYTECODE_ADDR_OFFSET)
        active_slot=0
        if gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_1 :
            active_slot = 1
        elif gpr_byte_code_value == b43.PARAMETER_ADDR_OFFSET_BYTECODE_2 :
            active_slot = 2
        else :
            self.log.error('startBootStrapOperation(): no active slot')
            return False

        if active_slot == 1 :
            b43.shmMaskSet16(b43.B43_SHM_REGS, b43.GPR_CONTROL, 0xF0FF, 0x0100)
        else :
            b43.shmMaskSet16(b43.B43_SHM_REGS, b43.GPR_CONTROL, 0xF0FF, 0x0200)
        while 1 :
            control_return = b43.shmRead16(b43.B43_SHM_REGS, b43.GPR_CONTROL)
            if (control_return & 0x0F00) == 0 :
                break

        return True
#
#
#     """
#     UPI_N implementation
#     """
#     def helper_parseIperf(self, iperfOutput):
#         """Parse iperf output and return bandwidth.
#            iperfOutput: string
#            returns: result string"""
#         import re
#
#         r = r'([\d\.]+ \w+/sec)'
#         m = re.findall( r, iperfOutput )
#         #self.log.debug("iperfOutput : %s " % iperfOutput)
#         #self.log.debug("m : %s " % m)
#         if m:
#             return m[-1]
#         else:
#             return None
#
#
#
#     def setRfChannel(self, myargs):
#         import subprocess
#
#         iface = myargs["iface"]
#         channel = myargs["channel"]
#
#         self.log.debug('setting channel(): %s->%s' % (str(iface), str(channel)))
#
#         cmd_str = 'sudo iwconfig ' + iface + ' channel ' + str(channel)
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         return True
#
#     def connectToAP(self, myargs):
#         import subprocess
#
#         iface = myargs["iface"]
#         ssid = myargs["ssid"]
#
#         self.log.info('connecting via to AP with SSID: %s->%s' % (str(iface), str(ssid)))
#
#         cmd_str = 'sudo iwconfig ' + iface + ' essid ' + str(ssid)
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         return True
#
#     def setEdcaParameters(self, myargs):
#         import pickle
#         import subprocess
#         self.log.debug('Slave: setEdcaParameters')
#         self.log.debug('margs = %s' % str(myargs))
#
#         ifname = myargs["interface"]
#         queueId = myargs["queueId"]
#         qParam = pickle.loads(myargs["qParam"])
#
#         cmd_str = ('sudo iw ' + ifname + ' info')
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         for item in cmd_output.split("\n"):
#              if "wiphy" in item:
#                 line = item.strip()
#
#         phyId = [int(s) for s in line.split() if s.isdigit()][0]
#
#         try:
#             myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/txq_params', 'w')
#         except Exception as e:
#             self.log.fatal("Operation not supported: %s" % e)
#             msg = {"ReturnValue": "ERROR"}
#             return msg
#
#         value = str(queueId) + " " + str(qParam.getAifs()) + " " + str(qParam.getCwMin()) + " " + str(qParam.getCwMax()) + " " + str(qParam.getTxOp())
#         myfile.write(value)
#         myfile.close()
#
#         msg = {"ReturnValue": "OK"}
#         return msg
#
#     def getEdcaParameters(self, myargs):
#         import pickle
#         import subprocess
#         self.log.debug('Slave: getEdcaParameters')
#         self.log.debug('margs = %s' % str(myargs))
#
#         ifname = myargs["interface"]
#
#         cmd_str = ('sudo iw ' + ifname + ' info')
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         for item in cmd_output.split("\n"):
#              if "wiphy" in item:
#                 line = item.strip()
#
#         phyId = [int(s) for s in line.split() if s.isdigit()][0]
#
#         try:
#             myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/txq_params', 'r')
#         except Exception as e:
#             self.log.fatal("Operation not supported: %s" % e)
#             msg = {"ReturnValue": "ERROR"}
#             return msg
#
#         data = myfile.read()
#         myfile.close()
#
#         msg = {"Data": data}
#         return msg
#
#     def cleanPerFlowTxPowerList(self, myargs):
#         self.log.debug('Slave: getPerFlowTxPowerList')
#         self.log.debug('margs = %s' % str(myargs))
#         ifname = myargs["interface"]
#
#         cmd_str = ('sudo iw ' + ifname + ' info')
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         for item in cmd_output.split("\n"):
#              if "wiphy" in item:
#                 line = item.strip()
#
#         phyId = [int(s) for s in line.split() if s.isdigit()][0]
#
#         try:
#             myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'w')
#         except Exception as e:
#             self.log.fatal("Operation not supported: %s" % e)
#             msg = {"ReturnValue": "ERROR"}
#             return msg
#
#         value = "0 0 0"
#         myfile.write(value)
#         myfile.close()
#
#         msg = {"ReturnValue": "OK"}
#         return msg
#
#     def getPerFlowTxPowerList(self, myargs):
#         import pickle
#         self.log.debug('Slave: getPerFlowTxPowerList')
#         self.log.debug('margs = %s' % str(myargs))
#         ifname = myargs["interface"]
#
#         cmd_str = ('sudo iw ' + ifname + ' info')
#         cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
#
#         for item in cmd_output.split("\n"):
#              if "wiphy" in item:
#                 line = item.strip()
#
#         phyId = [int(s) for s in line.split() if s.isdigit()][0]
#
#         try:
#             myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'r')
#         except Exception as e:
#             self.log.fatal("Operation not supported: %s" % e)
#             msg = {"ReturnValue": "ERROR"}
#             return msg
#
#         data = myfile.read()
#         myfile.close()
#
#         msg = {"Data": data}
#
#         return msg
#
#
#
#     def addSTAtoAPBlacklist(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def registerNewSTAInAP(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def changeRouting(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def getAvgSigPowerOfAssociatedSTAs(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def transmitDisassociationRequestToSTA(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def sendCSABeaconToSTA(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def performActiveSpectralScanning(self, param_key):
#         """
#         Performs on-demand spectrum scanning on the given channels. The results is a matrix where the rows are
#         freq, startfreq, noise, rssi, data, datasquaresum, highlight, signal
#         """
#         return
#
#     def startContinousSignal(self, param_key):
#         """
#         Generates a continous signal
#         """
#         return
#
#     def stopContinousSignal(self, param_key):
#         """
#         Generates a continous signal
#         """
#         return
#
#     def getInactivityTimeOfAssociatedSTAs(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def getInfoOfAssociatedSTAs(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def setARPEntry(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def removeSTAFromAPBlacklist(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#
#
#     """ return the MAC/HW address of a particular interface """
#
#     def getHwAddr(self, myargs):
#         import fcntl, socket, struct
#
#         iface = myargs["iface"]
#         s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', iface[:15]))
#         return ':'.join(['%02x' % ord(char) for char in info[18:24]])
#
#     """
#     Sends as fast as possible L2 broadcast traffic. Note: all transmitted packets are identical.
#     @return: the achieved transmit frame rate
#     """
#     def genBacklogged80211L2BcastTraffic(self, myargs):
#         self.log.info('genBacklogged80211L2BcastTraffic()')
#
#         iface = myargs["iface"]
#         num_packets = myargs["num_packets"]
#         ipPayloadSize = myargs["ipPayloadSize"]
#         phyBroadcastMbps = myargs["phyBroadcastMbps"]
#         ipdst = myargs["ipdst"]
#         ipsrc = myargs["ipsrc"]
#         use_tcpreplay = myargs["use_tcpreplay"]
#
#
#         # get my MAC HW address
#         myMacAddr = self.getHwAddr({'iface': iface})
#
#         # craft packet to be transmitted
#         payload = 'Z' * ipPayloadSize
#         data = RadioTap() / Dot11(type=2, subtype=0, addr1="ff:ff:ff:ff:ff:ff", addr2=myMacAddr, addr3=myMacAddr) \
#                / LLC() / SNAP() / IP(dst=ipdst, src=ipsrc) / payload
#
#
#         # # send 10 packets backlogged
#         now = datetime.now()
#         if use_tcpreplay:
#             # use tcprelay
#             sendpfast(data, iface=iface, mbps=phyBroadcastMbps, loop=num_packets, file_cache=True)
#         else:
#             piter = (len(data) * 8) / (phyBroadcastMbps * 1e6)
#             sendp(data, iface=iface, loop=1, inter=piter, realtime=True, count=num_packets, verbose=0)
#
#         delta = datetime.now()-now
#         # calc achieved transmit data rate
#         tx_frame_rate = 1.0 / ((delta.seconds + delta.microseconds / 1000000.0) / num_packets)
#
#         #addes by DG2016
#         tx_frame_rate = int(tx_frame_rate)
#         self.log.info('gen80211L2LinkProbing(): tx_frame_rate=%d' % tx_frame_rate)
#
#         return tx_frame_rate
#
#     """
#     Sends link probing traffic. Note: maximum number of packets is 255
#     """
#     def gen80211L2LinkProbing(self, myargs):
#
#         iface = myargs["iface"]
#         num_packets = myargs["num_packets"]
#         pinter = myargs["pinter"]
#         ipdst = myargs["ipdst"]
#         ipsrc = myargs["ipsrc"]
#
#         self.log.info('gen80211L2LinkProbing()')
#         # get my MAC HW address
#         myMacAddr = self.getHwAddr({'iface': iface})
#         dstMacAddr = 'ff:ff:ff:ff:ff:ff'
#
#         if num_packets > 255:
#             num_packets = 255
#
#         data = RadioTap() / Dot11(type=2, subtype=0, addr1=dstMacAddr, addr2=myMacAddr, addr3=myMacAddr) / LLC() / SNAP() / IP(dst=ipdst, src=ipsrc, ttl=(1,num_packets))
#         sendp(data, iface=iface, inter=pinter)
#
#     """
#     Sniffs link probing traffic.
#     @return returns the number of received packets
#     """
#     def sniff80211L2LinkProbing(self, myargs):
#
#         iface = myargs["iface"]
#         ipdst = myargs["ipdst"]
#         ipsrc = myargs["ipsrc"]
#         sniff_timeout = myargs["sniff_timeout"]
#
#         self.log.info('sniff80211L2LinkProbing()')
#         rx_pkts = {}
#         rx_pkts['res'] = 0
#
#         def ip_monitor_callback(pkt):
#             if IP in pkt and pkt[IP].src == ipsrc and pkt[IP].dst == ipdst:
#                 rx_pkts['res'] = rx_pkts['res'] + 1
#                 #return pkt.sprintf("{IP:%IP.src% -> %IP.dst% -> %IP.ttl%\n}")
#
#         sniff(iface=iface, prn=ip_monitor_callback, timeout=sniff_timeout)
#
#         numRxPkts = rx_pkts['res']
#         self.log.info('sniff80211L2LinkProbing(): rxpackets= %d' % numRxPkts)
#         return numRxPkts
#
#     """
#     Get IP address of a particular network interface
#     """
#     def getIfaceIpAddr(self, myargs):
#         import netifaces as ni
#
#         #iface = myargs["interface"]
#         if myargs.has_key('iface'):
#             iface = myargs["iface"]
#         if myargs.has_key('interface'):
#             iface = myargs["interface"]
#
#         #this function need the interface UP (modprobe b43)
#         ip = ni.ifaddresses(iface)[2][0]['addr']
#         return ip
#
#
#     """
#     UPI_R implementation specific for atheros
#     """
#     def installMacProcessor(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def updateMacProcessor(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     def uninstallMacProcessor(self, param_key):
#         """
#         Func Desc
#         """
#         return
#
#     """
#     UPI_N implementation
#     """
#     def getParameterHigherLayer(self, myargs):
#         cmd = myargs['cmd']
#         self.log.debug('getParameterHigherLayer(): %s' % str(cmd))
#         if cmd == UPI_N.IFACE_IP_ADDR:
#             return self.getIfaceIpAddr(myargs)
#         else:
#             self.log.error('getParameterHigherLayer(): unknown parameter')
#
#     def setParameterHigherLayer(self, myargs):
#         self.log.debug('setParameterHigherLayer(): %s->%s' % (str(myargs['cmd']), str(myargs)))
#         return True
#
#     def startIperfServer(self, myargs):
#         import os, sys, time, subprocess
#
#         self.log.debug('Slave: Start Iperf Server')
#
#         cmd = str("killall -9 iperf")
#         os.system(cmd);
#
#         throughput = None
#
#         cmd = ['/usr/bin/iperf','-s','-p', '5001']
#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#         lines_iterator = iter(process.stdout.readline, b"")
#         for line in lines_iterator:
#             throughput = self.helper_parseIperf(line)
#             if throughput:
#                 break
#
#         process.kill()
#         self.log.debug('Server side Throughput : ' + str(throughput))
#         sys.stdout.flush()
#         msg = {"type": "Server",
#             "throughput" : throughput}
#         return msg
#
#     def startIperfClient(self, myargs):
#         import os, sys, time, subprocess
#
#         self.log.debug('Slave: Start Iperf Client')
#         self.log.debug('margs = %s' % str(myargs))
#         ServerIp =  myargs['ServerIp']
#
#         throughput = None
#
#         cmd = ['/usr/bin/iperf','-c', ServerIp, '-p', '5001','-t','10']
#         process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#         lines_iterator = iter(process.stdout.readline, b"")
#         for line in lines_iterator:
#             throughput = self.helper_parseIperf(line)
#             if throughput:
#                 break
#
#         process.kill()
#         self.log.debug('Client Side Throughput : ' + str(throughput))
#         sys.stdout.flush()
#         msg = {"type": "Client",
#                 "throughput" : throughput}
#         return msg
#
#     def startPing(self, myargs):
#         import ping
#         import logging
#
#         log = logging.getLogger()
#         srcAddress =  myargs['srcAddress']
#         dstAddress =  myargs['dstAddres']
#         log.debug('Slave: Ping address: %s' % str(dstAddress))
#
#         [percentLost, maxRtt, avgRtt] = ping.quiet_ping(dest_addr=dstAddress,
#             interval = 0.2, count = 10, timeout = 2)
#
#         log.debug('Connection to {0} : AvgDelay={1}, MaxDelay={2}, Loss={3}'
#             .format(str(dstAddress), str(avgRtt), str(maxRtt), str(percentLost)))
#
#         msg = {
#             "SrcAddress" : srcAddress,
#             "DstAddres" : dstAddress,
#             "AvgRtt" : avgRtt,
#             "MaxRtt" : maxRtt,
#             "Loss" : percentLost
#         }
#
#         return msg
#
#     def setProfile(self, myargs):
#         import pickle
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: setProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#         profile = pickle.loads(myargs["profile"])
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.setProfile(profile)
#
#
#     def updateProfile(self, myargs):
#         import pickle
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: updateProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#         profile = pickle.loads(myargs["profile"])
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.updateProfile(profile)
#
#
#     def removeProfile(self, myargs):
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: removeProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.clean()
#
#
#     def setPerLinkProfile(self, myargs):
#         import pickle
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: setPerLinkProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#         dstNodeIp = myargs["dstNodeIp"]
#         profile = pickle.loads(myargs["profile"])
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.setPerLinkProfile(profile, dstNodeIp)
#
#
#     def updatePerLinkProfile(self, myargs):
#         import pickle
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: updatePerLinkProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#         dstNodeIp = myargs["dstNodeIp"]
#         profile = pickle.loads(myargs["profile"])
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.updatePerLinkProfile(profile, dstNodeIp)
#
#
#     def removePerLinkProfile(self, myargs):
#         from pytc.TrafficControl import TrafficControl
#         from pytc.Profile import Profile
#
#         log = logging.getLogger()
#         log.info('Function: removePerLinkProfile')
#         log.info('margs = %s' % str(myargs))
#         interface = myargs["interface"]
#         dstNodeIp = myargs["dstNodeIp"]
#
#         tcMgr = TrafficControl()
#         intface = tcMgr.getInterface(interface)
#         intface.cleanPerLinkProfile(dstNodeIp)
#
#
#     def installEgressScheduler(self, myargs):
#         from pytc.TrafficControl import TrafficControl
#         import pytc.Qdisc
#         import pytc.Filter
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: installEgressScheduler')
#         log.info('margs = %s' % str(myargs))
#
#         interface = myargs["interface"]
#         scheduler = pickle.loads(myargs["scheduler"])
#
#         tcMgr = TrafficControl()
#         iface = tcMgr.getInterface(interface)
#         iface.setEgressScheduler(scheduler)
#
#     def removeEgressScheduler(self, myargs):
#         from pytc.TrafficControl import TrafficControl
#         import pytc.Qdisc
#         import pytc.Filter
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: removeEgressScheduler')
#         log.info('margs = %s' % str(myargs))
#
#         interface = myargs["interface"]
#
#         tcMgr = TrafficControl()
#         iface = tcMgr.getInterface(interface)
#         iface.clean()
#         tcMgr.cleanIpTables()
#
#     def clearIpTables(self, myargs):
#         from pytc.Filter import FlowDesc
#         import iptc
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: clearIpTables')
#         log.info('margs = %s' % str(myargs))
#
#         table = myargs["table"]
#         chain = myargs["chain"]
#
#         tables = []
#         chains = {}
#
#         if table == "ALL":
#             tables = ["raw", "mangle", "nat", "filter"]
#         else:
#             if not isinstance(table, list):
#                 table = [table]
#             tables.extend(table)
#
#         if chain == "ALL":
#             chains["filter"] = ["INPUT","FORWARD","OUTPUT"]
#             chains["nat"] = ["PREROUTING", "OUTPUT", "POSTROUTING"]
#             chains["mangle"] = ["PREROUTING", "OUTPUT", "INPUT", "FORWARD", "POSTROUTING"]
#             chains["raw"] = ["PREROUTING", "OUTPUT"]
#         else:
#             if not isinstance(chain, list):
#                 chain = [chain]
#             chains[tables[0]].extend(chain)
#
#         for tableName in tables:
#             for chainName in chains[tableName]:
#                 chain = iptc.Chain(iptc.Table(tableName), chainName)
#                 chain.flush()
#
#
#     def getIpTable(self, myargs):
#         import iptc
#         import logging
#         import pickle
#         import copy
#
#         log = logging.getLogger()
#         log.info('Function: getIpTable')
#         log.info('margs = %s' % str(myargs))
#         tableName = myargs["table"]
#         chainName = myargs["chain"]
#
#         # exec embedded function
#         table = iptc.Table(tableName)
#         #refresh table to get current counters
#         table.refresh()
#         #create simple table (ie. without pointers to ctypes)
#         simpleTable = iptc.SimpleTable(table)
#         return pickle.dumps(simpleTable)
#
#     def setMarking(self, myargs):
#         from pytc.Filter import FlowDesc
#         import iptc
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: setMarking')
#         log.info('margs = %s' % str(myargs))
#
#         flowDesc = pickle.loads(myargs["flowDesc"])
#         if "markId" in myargs:
#             markId = myargs["markId"]
#         else:
#             tcMgr = TrafficControl()
#             markId = tcMgr.generateMark()
#
#         if "table" in myargs:
#             table = myargs["table"]
#         else:
#             table = "mangle"
#
#         if "chain" in myargs:
#             chain = myargs["chain"]
#         else:
#             chain = "POSTROUTING"
#
#         rule = iptc.Rule()
#
#         if flowDesc.mSrcAddress is not None:
#             rule.src = flowDesc.mSrcAddress
#
#         if flowDesc.mDstAddress is not None:
#             rule.dst = flowDesc.mDstAddress
#
#         if flowDesc.mProt is not None:
#             rule.protocol = flowDesc.mProt
#             match = iptc.Match(rule, flowDesc.mProt)
#
#             if flowDesc.mSrcPort is not None:
#                 match.sport = flowDesc.mSrcPort
#
#             if flowDesc.mDstPort is not None:
#                 match.dport = flowDesc.mDstPort
#
#             rule.add_match(match)
#
#         target = iptc.Target(rule, "MARK")
#         target.set_mark = str(markId)
#         rule.target = target
#         chain = iptc.Chain(iptc.Table(table), chain)
#         chain.insert_rule(rule)
#
#     def delMarking(self, myargs):
#         from pytc.Filter import FlowDesc
#         import iptc
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: delMarking')
#         log.info('margs = %s' % str(myargs))
#
#         flowDesc = pickle.loads(myargs["flowDesc"])
#         markId = myargs["markId"]
#         chain = myargs["chain"]
#         table = myargs["table"]
#
#         rule = iptc.Rule()
#
#         if flowDesc.mSrcAddress is not None:
#             rule.src = flowDesc.mSrcAddress
#
#         if flowDesc.mDstAddress is not None:
#             rule.dst = flowDesc.mDstAddress
#
#         if flowDesc.mProt is not None:
#             rule.protocol = flowDesc.mProt
#             match = iptc.Match(rule, flowDesc.mProt)
#
#             if flowDesc.mSrcPort is not None:
#                 match.sport = flowDesc.mSrcPort
#
#             if flowDesc.mDstPort is not None:
#                 match.dport = flowDesc.mDstPort
#
#             rule.add_match(match)
#
#         target = iptc.Target(rule, "MARK")
#         target.set_mark = str(markId)
#         rule.target = target
#         chain = iptc.Chain(iptc.Table(table), chain)
#         chain.delete_rule(rule)
#
#     def setTos(self, myargs):
#         from pytc.Filter import FlowDesc
#         import iptc
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: setTos')
#         log.info('margs = %s' % str(myargs))
#
#         flowDesc = pickle.loads(myargs["flowDesc"])
#         tos = myargs["tos"]
#         chain = myargs["chain"]
#         table = myargs["table"]
#
#         rule = iptc.Rule()
#
#         if flowDesc.mSrcAddress is not None:
#             rule.src = flowDesc.mSrcAddress
#
#         if flowDesc.mDstAddress is not None:
#             rule.dst = flowDesc.mDstAddress
#
#         if flowDesc.mProt is not None:
#             rule.protocol = flowDesc.mProt
#             match = iptc.Match(rule, flowDesc.mProt)
#
#             if flowDesc.mSrcPort is not None:
#                 match.sport = flowDesc.mSrcPort
#
#             if flowDesc.mDstPort is not None:
#                 match.dport = flowDesc.mDstPort
#
#             rule.add_match(match)
#
#         target = iptc.Target(rule, "TOS")
#         target.set_tos = str(tos)
#         rule.target = target
#         chain = iptc.Chain(iptc.Table(table), chain)
#         chain.insert_rule(rule)
#
#
#     def delTos(self, myargs):
#         from pytc.Filter import FlowDesc
#         import iptc
#         import pickle
#
#         log = logging.getLogger()
#         log.info('Function: delTos')
#         log.info('margs = %s' % str(myargs))
#
#         flowDesc = pickle.loads(myargs["flowDesc"])
#         tos = myargs["tos"]
#         chain = myargs["chain"]
#         table = myargs["table"]
#
#         rule = iptc.Rule()
#
#         if flowDesc.mSrcAddress is not None:
#             rule.src = flowDesc.mSrcAddress
#
#         if flowDesc.mDstAddress is not None:
#             rule.dst = flowDesc.mDstAddress
#
#         if flowDesc.mProt is not None:
#             rule.protocol = flowDesc.mProt
#             match = iptc.Match(rule, flowDesc.mProt)
#
#             if flowDesc.mSrcPort is not None:
#                 match.sport = flowDesc.mSrcPort
#
#             if flowDesc.mDstPort is not None:
#                 match.dport = flowDesc.mDstPort
#
#             rule.add_match(match)
#
#         target = iptc.Target(rule, "TOS")
#         target.set_tos = str(tos)
#         rule.target = target
#         chain = iptc.Chain(iptc.Table(table), chain)
#         chain.delete_rule(rule)
#
#     def installApplication(self, myargs):
#         import pickle
#         from helpers.application import ServerApplication, ClientApplication
#
#         log = logging.getLogger()
#         log.info('Function: installApplication')
#         log.info('margs = %s' % str(myargs))
#
#         app = pickle.loads(myargs["app"])
#         appType = app.type
#         port = app.port
#         protocol = app.protocol
#
#
#         if appType == "Server":
#             log.info('Installing Server application')
#
#             #cmd = str("killall -9 iperf")
#             #os.system(cmd);
#             bind = app.bind
#
#             cmd = ['/usr/bin/iperf','-s','-i','1']
#             if protocol == "TCP":
#                 pass
#             elif protocol == "UDP":
#                 cmd.extend(['-u'])
#
#             if port:
#                 cmd.extend(['-p', str(port)])
#
#             if bind:
#                 cmd.extend(['-B', str(bind)])
#
#             cmd.extend(['--reportstyle','C'])
#             cmd.extend(['>iperf_server.log'])
#
#             # throughput = None
#             # process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#             # lines_iterator = iter(process.stdout.readline, b"")
#             # for line in lines_iterator:
#             #     throughput = self.helper_parseIperf(line)
#             #     if throughput:
#             #         break
#
#             self.log.warning(" cmd string : %s", str(cmd))
#             num_res = 0
#             #TODO start from zero and increase this variable when a connecton is detected
#             num_of_connection = 2
#             flag = 0
#             throughput = 0
#             process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#             lines_iterator = iter(process.stdout.readline, b"")
#             for line in lines_iterator:
#                  filename = 'file_log.csv'
#                  if flag == 0:
#                     out_file = open(filename, 'w')
#                     flag = 1
#                     out_file.write(line)
#                  else:
#                     out_file = open(filename, 'a')
#                     out_file.write(line)
#
# #                self.log.debug("line: %s", line)
#                  throughput = self.helper_parseIperf(line)
#                  if throughput:
#
#                     if num_res == num_of_connection:
#                         break
#                     else:
#                         num_res += 1
#
#             process.kill()
#             self.log.debug('Server side Throughput : ' + str(throughput))
#             sys.stdout.flush()
#             msg = {"type": "Server",
#                 "throughput" : throughput}
#             return msg
#
#         elif appType == "Client":
#             log.info('Installing Client application')
#
#             serverIp =  app.destination
#             udpBandwidth = app.udpBandwidth
#             dualTest = app.dualtest
#             dataToSend = app.dataToSend
#             transmissionTime = app.transmissionTime
#             frameLen = app.frameLen
#
#             cmd = ['/usr/bin/iperf','-c', serverIp]
#
#             if protocol == "TCP":
#                 pass
#             elif protocol == "UDP":
#                 cmd.extend(['-u'])
#                 if udpBandwidth:
#                     cmd.extend(['-b', str(udpBandwidth)])
#
#             if port:
#                 cmd.extend(['-p', str(port)])
#
#             if dualTest:
#                 cmd.extend(['-d'])
#
#             if dataToSend:
#                 cmd.extend(['-n', str(dataToSend)])
#
#             if transmissionTime:
#                 cmd.extend(['-t', str(transmissionTime)])
#
#             if frameLen:
#                 cmd.extend(['-l', str(frameLen)])
#
#             throughput = None
#             process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#             lines_iterator = iter(process.stdout.readline, b"")
#             for line in lines_iterator:
#                 throughput = self.helper_parseIperf(line)
#                 if throughput:
#                     break
#
#             process.kill()
#             self.log.debug('Client Side Throughput : ' + str(throughput))
#             sys.stdout.flush()
#             msg = {"type": "Client",
#                     "throughput" : throughput}
#             return msg
#
#         elif appType == "RawperfClient":
#             log.info('Installing Rawperf Client application')
#
#             serverMAC =  app.destination
#             udpBandwidth = app.udpBandwidth
#             dualTest = app.dualtest
#             dataToSend = app.dataToSend
#             waitTime = app.waitTime
#             frameLen = app.frameLen
#             transmissionTime = app.transmissionTime
#
#             cmd = ['./runtime/connectors/wmp_linux/network_script/association.sh','-s', serverMAC]
#
#             if transmissionTime:
#                 cmd.extend(['-t', str(transmissionTime)])
#
#             if waitTime:
#                 cmd.extend(['-w', str(waitTime)])
#
#             if frameLen:
#                 cmd.extend(['-l', str(frameLen)])
#
#             # throughput = None
#             process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
#             # lines_iterator = iter(process.stdout.readline, b"")
#             # for line in lines_iterator:
#             #     throughput = self.helper_parseIperf(line)
#             #     if throughput:
#             #         break
#
#             time.sleep(waitTime)
#             process.kill()
#
#             # self.log.debug('Client Side Throughput : ' + str(throughput))
#             # sys.stdout.flush()
#             # msg = {"type": "Client",
#             #         "throughput" : throughput}
#             msg = {"type": "RawperfClient",
#                      "throughput" : "NULL"}
#
#             return msg
#
#         else:
#             log.info('Application Type not supported')
#
#     def getNetworkInfo(self,myargs):
#         raise ValueError('Not yet implemented')



    # @wishful_module.bind_function(upis.radio.set_mac_access_parameters)
    # def setEdcaParameters(self, queueId, queueParams):
    #     self.log.debug("ATH9K sets EDCA parameters for queue: {} on interface: {}".format(queueId, self.interface))
    #
    #     self.log.debug("AIFS: {}".format(queueParams.getAifs()))
    #     self.log.debug("CwMin: {}".format(queueParams.getCwMin()))
    #     self.log.debug("CwMax: {}".format(queueParams.getCwMax()))
    #     self.log.debug("TxOp: {}".format(queueParams.getTxOp()))
    #
    #     cmd_str = ('sudo iw ' + self.interface + ' info')
    #     cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
    #
    #     for item in cmd_output.split("\n"):
    #          if "wiphy" in item:
    #             line = item.strip()
    #
    #     phyId = [int(s) for s in line.split() if s.isdigit()][0]
    #
    #     try:
    #         myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/txq_params', 'w')
    #         value = str(queueId) + " " + str(queueParams.getAifs()) + " " + str(queueParams.getCwMin()) + " " + str(queueParams.getCwMax()) + " " + str(queueParams.getTxOp())
    #         myfile.write(value)
    #         myfile.close()
    #         return "OK"
    #     except Exception as e:
    #         self.log.fatal("Operation not supported: %s" % e)
    #         raise exceptions.UPIFunctionExecutionFailedException(func_name='radio.set_mac_access_parameters', err_msg='cannot open file')
    #
    #
    #
    # @wishful_module.bind_function(upis.radio.get_mac_access_parameters)
    # def getEdcaParameters(self):
    #     self.log.debug("ATH9K gets EDCA parameters for interface: {}".format(self.interface))
    #
    #     cmd_str = ('sudo iw ' + self.interface + ' info')
    #     cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
    #
    #     for item in cmd_output.split("\n"):
    #          if "wiphy" in item:
    #             line = item.strip()
    #
    #     phyId = [int(s) for s in line.split() if s.isdigit()][0]
    #
    #     try:
    #         myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/txq_params', 'r')
    #         data = myfile.read()
    #         myfile.close()
    #         return data
    #     except Exception as e:
    #         self.log.fatal("Operation not supported: %s" % e)
    #         raise exceptions.UPIFunctionExecutionFailedException(func_name='radio.get_mac_access_parameters', err_msg='cannot open file')
    #
    #
    # @wishful_module.bind_function(upis.radio.set_per_flow_tx_power)
    # def set_per_flow_tx_power(self, flowId, txPower):
    #     self.log.debug('set_per_flow_tx_power on iface: {}'.format(self.interface))
    #
    #     tcMgr = TrafficControl()
    #     markId = tcMgr.generateMark()
    #     self.setMarking(flowId, table="mangle", chain="POSTROUTING", markId=markId)
    #
    #     cmd_str = ('sudo iw ' + self.interface + ' info')
    #     cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
    #
    #     for item in cmd_output.split("\n"):
    #          if "wiphy" in item:
    #             line = item.strip()
    #
    #     phyId = [int(s) for s in line.split() if s.isdigit()][0]
    #
    #     try:
    #         myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'w')
    #         value = str(markId) + " " + str(txPower) + " 0"
    #         myfile.write(value)
    #         myfile.close()
    #         return "OK"
    #     except Exception as e:
    #         self.log.fatal("Operation not supported: %s" % e)
    #         raise exceptions.UPIFunctionExecutionFailedException(func_name='radio.set_per_flow_tx_power', err_msg='cannot open file')
    #
    #
    # def setMarking(self, flowId, table="mangle", chain="POSTROUTING", markId=None):
    #
    #     if not markId:
    #         tcMgr = TrafficControl()
    #         markId = tcMgr.generateMark()
    #
    #     rule = iptc.Rule()
    #
    #     if flowId.srcAddress:
    #         rule.src = flowId.srcAddress
    #
    #     if flowId.dstAddress:
    #         rule.dst = flowId.dstAddress
    #
    #     if flowId.prot:
    #         rule.protocol = flowId.prot
    #         match = iptc.Match(rule, flowId.prot)
    #
    #         if flowId.srcPort:
    #             match.sport = flowId.srcPort
    #
    #         if flowId.dstPort:
    #             match.dport = flowId.dstPort
    #
    #         rule.add_match(match)
    #
    #     target = iptc.Target(rule, "MARK")
    #     target.set_mark = str(markId)
    #     rule.target = target
    #     chain = iptc.Chain(iptc.Table(table), chain)
    #     chain.insert_rule(rule)
    #
    #
    # @wishful_module.bind_function(upis.radio.clean_per_flow_tx_power_table)
    # def clean_per_flow_tx_power_table(self):
    #     self.log.debug('clean_per_flow_tx_power_table on iface: {}'.format(self.interface))
    #
    #     cmd_str = ('sudo iw ' + self.interface + ' info')
    #     cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
    #
    #     for item in cmd_output.split("\n"):
    #          if "wiphy" in item:
    #             line = item.strip()
    #
    #     phyId = [int(s) for s in line.split() if s.isdigit()][0]
    #
    #     try:
    #         myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'w')
    #         value = "0 0 0"
    #         myfile.write(value)
    #         myfile.close()
    #         return "OK"
    #     except Exception as e:
    #         self.log.fatal("Operation not supported: %s" % e)
    #         raise exceptions.UPIFunctionExecutionFailedException(func_name='radio.clean_per_flow_tx_power_table', err_msg='cannot open file')
    #
    #
    # @wishful_module.bind_function(upis.radio.get_per_flow_tx_power_table)
    # def get_per_flow_tx_power_table(self):
    #     self.log.debug('get_per_flow_tx_power_table on iface: {}'.format(self.interface))
    #
    #     cmd_str = ('sudo iw ' + self.interface + ' info')
    #     cmd_output = subprocess.check_output(cmd_str, shell=True, stderr=subprocess.STDOUT)
    #
    #     for item in cmd_output.split("\n"):
    #          if "wiphy" in item:
    #             line = item.strip()
    #
    #     phyId = [int(s) for s in line.split() if s.isdigit()][0]
    #
    #     try:
    #         myfile = open('/sys/kernel/debug/ieee80211/phy'+str(phyId)+'/ath9k/per_flow_tx_power', 'r')
    #         data = myfile.read()
    #         myfile.close()
    #         return data
    #     except Exception as e:
    #         self.log.fatal("Operation not supported: %s" % e)
    #         raise exceptions.UPIFunctionExecutionFailedException(func_name='radio.get_per_flow_tx_power_table', err_msg='cannot open file')
    #
    #
    # @wishful_module.bind_function(upis.radio.get_noise)
    # def get_noise(self):
    #     self.log.debug("Get Noise".format())
    #     return random.randint(-120, -30)
    #
    #
    # @wishful_module.bind_function(upis.radio.get_airtime_utilization)
    # def get_airtime_utilization(self):
    #     self.log.debug("Get Airtime Utilization".format())
    #     return random.random()
    #
    #
    # @wishful_module.bind_function(upis.radio.perform_spectral_scanning)
    # def perform_spectral_scanning(self, iface, freq_list, mode):
    #     """
    #         Perform active spectral scanning
    #     """
    #
    #     self.log.debug('performActiveSpectralScanning on iface %s for freq=%s' % (iface, freq_list))
    #
    #     exec_file = str(os.path.join(self.getPlatformPathSpectralScan())) + '/scan.sh'
    #     command = exec_file + " " + iface + " /tmp/out \"" + freq_list + "\""
    #
    #     self.log.debug('command: %s' % command)
    #
    #     try:
    #         # perform scanning
    #         [rcode, sout, serr] = self.run_command(command)
    #
    #         if serr:
    #             self.log.warn("standard error of subprocess:")
    #             self.log.warn(serr)
    #             raise Exception("Error occured during spectrum scanning: %s" % serr)
    #
    #         # perform parsing results
    #         self.log.debug('parsing scan results ...')
    #
    #         tmpfile = '/tmp/out.dat'
    #         res = []
    #         with open(tmpfile) as f:
    #             content = f.readlines()
    #
    #             for line in content:
    #                 arr = line.split(',')
    #                 res.append(arr)
    #
    #         # cleanup
    #         os.remove(tmpfile)
    #
    #         self.log.info('spec scan size %d' % len(res))
    #
    #         if mode == 0:
    #             # return just raw samples
    #             return res
    #         elif mode == 1:
    #             # return the max/mean signal for each frequency bin only
    #             y = np.array(res)
    #             y = y.astype(np.float)
    #             uniq_freq = np.unique(y[:,0])
    #             uniq_freq.sort(axis=0)
    #             ret = []
    #             for v in np.nditer(uniq_freq.T):
    #                 v2 = np.asscalar(v)
    #
    #                 a = y[np.logical_or.reduce([y[:,0] == x for x in (v2,)])]
    #                 sig = a[:,7].astype(np.float)
    #                 max_sig = 100
    #                 sig = sig[sig < max_sig]
    #
    #                 max_v = np.ndarray.max(sig)
    #                 mean_v = np.ndarray.mean(sig)
    #
    #                 #print('max: ', max_v)
    #                 #print('mean: ', mean_v)
    #                 ret.append([np.asscalar(v), max_v, mean_v])
    #
    #             return ret
    #         else:
    #             raise Exception("Unknown mode type %s" % str(mode))
    #
    #     except Exception as e:
    #         self.log.fatal("An error occurred in Dot80211Linux: %s" % e)
    #         raise Exception("An error occurred in Dot80211Linux: %s" % e)
    #
    #
    # #################################################
    # # Helper functions
    # #################################################
    #
    # def getPlatformPathSpectralScan(self):
    #     """
    #     Path to platform dependent (native) binaries: here spectral scanning
    #     """
    #     PLATFORM_PATH = os.path.join(".", "runtime", "connectors", "dot80211_linux", "ath_spec_scan", "bin")
    #     pl = platform.architecture()
    #     sys = platform.system()
    #     machine = platform.machine()
    #     return os.path.join(PLATFORM_PATH, sys, pl[0], machine)
