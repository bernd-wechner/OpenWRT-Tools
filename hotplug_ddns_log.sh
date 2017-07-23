#!/bin/sh
# Logs the new WANIP when the network interface goes up. 
# Should run after the OpenWRT: /etc/hotplug.d/iface/95-ddns
# For example residing as /etc/hotplug.d/iface/96-ddns-log

case "$ACTION" in
	ifup)
		log_wanip ifup
		;;
esac
