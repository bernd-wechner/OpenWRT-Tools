#!/bin/sh
# Logs the new WANIP when the network interface goes up. 
# Should be in the path of the hotplug daemon and cron
#
# TODO: Send email when WANIP is seen to change. 
# Write a DDNS checker (that uses ddnsip -e?) and sends an email if an error is seen.
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
	url="$urlbase?wanip=$wanip&reason=$reason&key=$APIkey"

	result=$(curl -s $url)

	echo $wanip > $ipdir/$ipfile
	echo $result >> $logdir/$logfile
fi