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
iwconfig $dev essid $essid
#iw dev $dev connect $essid

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

iwconfig $dev rate 2M fixed
#iwconfig $dev rate 12M fixed
iwconfig $dev txpower 15dBm
echo association successful

set +x
