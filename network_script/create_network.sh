#!/bin/bash
set -x

#kill hostapd
killall -9 hostapd

#set network interfare
ip_addr=$1
ifconfig wlan0 $ip_addr netmask 255.255.255.0
iwconfig wlan0 rate 24M fixed
iwconfig wlan0   txpower 15dBm

#run hostapd
hostapd  ../../../agent_modules/wifi_wmp/network_script/hostapd2.conf

set +x