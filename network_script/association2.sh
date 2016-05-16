#!/bin/bash
set -x

ip=$2
ssid_name=$1
dev="wlan0"

ifconfig $dev $ip netmask 255.255.255.0
ifconfig $dev up
iwconfig $dev essid $ssid_name
iwconfig $dev rate 11M fixed
iwconfig $dev txpower 15dBm
ifconfig $dev $ip netmask 255.255.255.0
set +x
