#!/bin/bash
set -x
ip_addr=$1
ifconfig wlan0 $ip_addr netmask 255.255.255.0
iwconfig wlan0 rate 24M fixed
iwconfig wlan0   txpower 15dBm
#sleep 1
#hostapd ./hostapd2.conf >/dev/null 2>&1
hostapd  /root/wishful_upis/runtime/connectors/wmp_linux/network_script/hostapd2.conf
set +x