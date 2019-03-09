#!/bin/bash
# Logs the new WANIP when the network interface goes up.
# Should be in the path of the hotplug daemon and cron
#
# Takes one argument, the reason for sending the log.

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

wanip=""
tries=0

# WAN IP may not be available the second the ifup event triggers a hotplug
# Retry until it is or a time is up (30mins)
while [[ "$wanip" == "" ]] && (( tries < 60 )); do
	wanip=$(wanip -4)
	if [[ "$wanip" == "" ]]; then sleep 30; fi
	(( tries++ ))
done

# If we still don't have it, say so with clarity.
if [[ "$wanip" == "" ]]; then wanip="unknown"; fi

# Fetch the last seen WAN IP
lastip=$(cat $ipdir/$ipfile)

if [[ "$wanip" != "$lastip" ]]; then
	result=$(curl -sG $urlbase --data-urlencode "wanip=$wanip" --data-urlencode "reason=$reason" --data-urlencode "key=$APIkey")

	echo $wanip > $ipdir/$ipfile
	echo $result >> $logdir/$logfile

	# Send a notification email:
	#
	# This is Omnia specific and uses it's notification system to send and email
	# Settings can be found with "uci -q show user_notify" and set with uci or
	# through the Foris web interface under Maintenance. Email notifications
	# have to be enabled there.
	nl=$'\n'
	msg=$"WAN IP changed from $lastip to $wanip${nl}${nl}Event was logged as:${nl}${nl}$result${nl}${nl}locally in $logdir/$logfile${nl}remotely at $urlbase${nl}See a history at ${urlbase}?wanip"
	create_notification -s news "" "$msg"

	# Run the notifier to send the message now (by default Omnia schedules it pretty often but I want to
	# see WANIP updates ASAP. So we run it explicitly to send the email now.
	notifier
fi
