#! /bin/bash
channel=$1
dev="wlan0"
set -x
	rmmod b43
	modprobe b43 qos=0 hwpctl=1
	iwconfig $dev mode monitor
	ifconfig $dev up
	iwconfig $dev channel $channel
	iwconfig $dev txpower 30dbm
set +x
