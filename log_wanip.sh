#!/bin/bash
# Logs the new WANIP when the network interface goes up.
# Should be in the path of the hotplug daemon and cron
#
# Takes one argument, the reason for sending the log.

# Records the last WAN IP seen, only log it if has changed from this
#
# TOD Add command line arguments with getopts
#
# -f to force logging

ipdir='/srv/wan'
ip4file='ip4'
ip6file='ip6'

if [ ! -d $ipdir ]; then
    mkdir -p $ipdir
fi

# Logs all updates sent (the reponse thereof)
logdir='/mnt/sda1/log/ddns'
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

# Fetch the WAN IPs

wanip4=""
wanip6=""
tries=0

# WAN IP may not be available the second the ifup event triggers a hotplug
# Retry until it is or a time is up (30mins)
while [[ "$wanip4" == "" ]] && (( tries < 60 )); do
	wanip4=$(wanip -4)
	if [[ "$wanip4" == "" ]]; then sleep 30; fi
	(( tries++ ))
done

while [[ "$wanip6" == "" ]] && (( tries < 60 )); do
	wanip6=$(wanip -6)
	if [[ "$wanip6" == "" ]]; then sleep 30; fi
	(( tries++ ))
done

# If we still don't have it, say so with clarity.
if [[ "$wanip4" == "" ]]; then wanip4="unknown"; fi
if [[ "$wanip6" == "" ]]; then wanip6="unknown"; fi

# Fetch the last seen WAN IPs
lastip4=$(cat $ipdir/$ip4file)
lastip6=$(cat $ipdir/$ip6file)

if [[ "$wanip4" != "$lastip4" ]] || [[ "$wanip6" != "$lastip6" ]]; then
	result=$(curl -sG $urlbase --data-urlencode "wanip4=$wanip4" --data-urlencode "wanip6=$wanip6" --data-urlencode "reason=$reason" --data-urlencode "key=$APIkey")

	echo $wanip4 > $ipdir/$ip4file
	echo $wanip6 > $ipdir/$ip6file
	echo $result >> $logdir/$logfile

	# Send a notification email:
	#
	# This is Omnia specific and uses it's notification system to send and email
	# Settings can be found with "uci -q show user_notify" and set with uci or
	# through the Foris web interface under Maintenance. Email notifications
	# have to be enabled there.
	nl=$'\n'
	msg=$"WAN IP changed from${nl}    $lastip4 to $wanip4${nl}and${nl}    $lastip6 to $wanip6${nl}${nl}Event was logged as:${nl}${nl}$result${nl}${nl}locally in $logdir/$logfile${nl}remotely at $urlbase${nl}See a history at ${urlbase}?wanip"
	create_notification -s news "" "$msg"

	# Run the notifier to send the message now (by default Omnia schedules it pretty often but I want to
	# see WANIP updates ASAP. So we run it explicitly to send the email now.
	notifier
fi
