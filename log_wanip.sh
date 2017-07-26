#!/bin/sh
# Logs the new WANIP when the network interface goes up. 
# Should be in the path of the hotplug daemon and cron
#
# Takes on argument, the reason for sending the log.
#
# TODO: Write a DDNS checker (that uses ddnsip -e?) and sends an email if an error is seen.
# Run that on an houry cron maybe, or daily. 

# Records the last WAN IP seen, only log it if has changed from this
ipdir='/srv/wan'
ipfile='ip'

if [ ! -d $ipdir ]; then
    mkdir -p $ipdir
fi

# Logs all updates sent (the reponse thereof)
logdir='/var/log/ddns'
logfile='wan_ip.log'  

if [ ! -d $logdir ]; then
    mkdir -p $logdir
fi

# URL points to a remote service that can accept the log
urlbase='https://thumbs-place.alwaysdata.net/ddns/'

# A reason for the update
reason=${1:-unspecified}

# fetch a key used to reduce risk of abusive submissions by third parties
# Expect this to define username and APIkey
keydir='/root/.auth'
keyfile='namecheap.auth'  

source $keydir/$keyfile

# Fetch the WAN IP
wanip=$(ip addr show pppoe-wan|grep inet|awk '{print $2}' | sed 's#/.*##')

# Fetch the last seen WAN IP
lastip=$(cat $ipdir/$ipfile)

if [ "$wanip" != "$lastip" ]; then
	result=$(curl -sG $urlbase --data-urlencode "wanip=$wanip" --data-urlencode "reason=$reason" --data-urlencode "key=$APIkey")
	
	echo $wanip > $ipdir/$ipfile
	echo $result >> $logdir/$logfile

	# Send a notification email:
	#
	# This is Omnia specific and uses it's notification system to send and email
	# Settings can be found with "uci -q show user_notify" and set with uci or
	# through the Foris web interface under Maintenance. Email notifications
	# have to be enabled there.
	msg="WAN IP changed from $lastip to $wanip\n\nEvent was logged as:\n\n$result\n\n\nlocally in $logdir/$logfile\nremotely at $urlbase" 
	create_notification -s news "" "$msg"
	
	# Run the notifier to send the message now (by default Onia schedules it pretty often but I want to 
	# see WANIP updates ASAP. So we run it explicitly to send the email now. 
	notifier
fi
