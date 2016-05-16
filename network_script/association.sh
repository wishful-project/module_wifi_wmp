#!/bin/bash

#if [ $# -lt 1 ]; then
#	echo "usage $0 <essid> <ip-addr>"
#	exit
#fi


essid=$1
ip=$2
dev="wlan0"

set -x

ifconfig $dev $ip netmask 255.255.255.0
#ifconfig $dev down
#ifconfig $dev hw ether 00:0d:b9:2d:a2:6a
#ifconfig $dev hw ether  00:14:a4:62:c8:1a
#ifconfig $dev $ip netmask 255.255.255.0 up

iwconfig $dev essid $essid
#iw dev $dev connect $essid
#sleep 3

for ((i=0; $i < 10; i= $((i+1)))) do

	#iwconfig $dev | grep Access
	IWCONFIG_RESULT=$(iwconfig $dev | grep Access | awk '{ print $4 }';);
	#echo iwconfig result $IWCONFIG_RESULT
	if [[ "$IWCONFIG_RESULT" != "Not-Associated" ]]; then
		break
	fi
	iwconfig $dev essid $essid
	#iw dev $dev connect $essid
	sleep 2

done

#ip route add 10.0.0.0/8 dev wlan0 proto kernel scope link src 10.163.8.232
#ip route add default via 10.163.8.229 dev wlan0

iwconfig $dev rate 11M fixed
#iwconfig $dev rate 12M fixed
iwconfig $dev txpower 15dBm
echo association successful

set +x
