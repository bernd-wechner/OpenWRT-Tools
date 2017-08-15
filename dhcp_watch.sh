#!/bin/bash
#
# A script for dnsmasq to run when DHCP leases are changed in any way.
#
# From the dnsmasq man page:
#
# Whenever a new DHCP lease is created, or an old one destroyed, or a TFTP file transfer completes, 
# the executable specified by this option is run. <path> must be an absolute pathname, no PATH search occurs.
# 
# The arguments to the process are 
# "add", "old" or "del", 
# the MAC address of the host (or DUID for IPv6), 
# the IP address, and 
# the hostname, if known. 
#
# "add" means a lease has been created, 
# "del" means it has been destroyed, 
# "old" is a notification of an existing lease when dnsmasq starts or 
#       a change to MAC address or hostname of an existing lease 
#       (also, lease length or expiry and client-id, if leasefile-ro is set). 
#
# If the MAC address is from a network type other than ethernet, it will have the network type prepended, eg "06-01:23:45:67:89:ab" for token ring. The process is run as root (assuming that dnsmasq was originally run as root) even if dnsmasq is configured to change UID to an unprivileged user.
#
# Configure dnsmasq to run this script by adding these lines to /etc/dnsmasq.conf on the router
#   # Run a script on every action
#   dhcp-script=/usr/bin/dhcp_watch
#
# Assuming this script is installed there. 

# Location of log
logdir='/var/log'
logfile='dhcp.log'  

# Get the arguments from dnsmasq 
op="${1:-unknown operation}"
mac="${2:-unknown mac}"
ip="${3:-unknown ip}"
hostname="${4:-unknown hostname}"

tstamp="`date '+%Y-%m-%d %H:%M:%S'`"

log="$tstamp $op $ip $mac ($hostname)"

echo $log >> $logdir/$logfile

# Given an IP address fetch the MAC address (if any) associated with it as a static DHCP lease
IP_MAC() {
	lanip DHCP | grep "\b$1\b" | awk '{print $3}'
}

# Given an IP address fetch the Host name (if any) associated with it as a static DHCP lease
IP_Hostname() {
	lanip DHCP | grep "\b$1\b" | awk '{print $1}'
}

# Post a notification if a new IP address is allocated AND if the MAC of an existing lease changes!
if [[ "$op" == "add" || "$op" == "old" ]]; then
	# Get static lease MAC and hostname associated with this IP if any
	ip_mac=$(IP_MAC $ip)
	ip_hostname=$(IP_Hostname $ip)
	
	# If we're assigning a different MAC  or hostname to a static lease IP something is awry
	# And if there was no static lease for this IP then ip_mac and ip_hostname are empty
	# Compare MAC addresses in upper case
	if [[ "${ip_mac^^}" !=  "${mac^^}" || "$ip_hostname" !=  "$hostname" ]]; then
		log="$tstamp Sending notification because requested MAC (${mac^^}) is not same as static lease MAC (${ip_mac^^}), or requested hostname ($hostname) is not same as static lease hostname ($ip_hostname)."
		echo $log >> $logdir/$logfile

		# Send a notification email:
		#
		# This is Omnia specific and uses it's notification system to send and email
		# Settings can be found with "uci -q show user_notify" and set with uci or
		# through the Foris web interface under Maintenance. Email notifications
		# have to be enabled there.
		nl=$'\n'

		# If it was a static lease
		if [[ "$ip_mac" != "" ]]; then
			add=". Static lease for ${ip_mac^^} ($ip_hostname)"
		else
			add=". No static lease."
		fi
		
		msg=$"DHCP allocated IP $ip to ${mac^^} ($hostname)$add"
		
		create_notification -s news "" "$msg"
		
		# Run the notifier to send the message now (by default Omnia schedules it pretty often but I want to 
		# see WANIP updates ASAP. So we run it explicitly to send the email now. 
		notifier
	fi
fi
