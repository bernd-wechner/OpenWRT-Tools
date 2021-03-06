#!/bin/bash
#
# Prints the apparent WAN address of this OpenWRT router
#
# -h: print a history of WAN IPs
# -4 prints the IPv4 WAN address only
# -6 prints the IPv6 WAN address only

# Records of WAN IP values seen, logged by log_wanip.sh
logdir='/var/log/ddns'
logfile='wan_ip.log'

function duration {
	local T=$1
	local Y=$((T/60/60/24/7/52))
	local W=$((T/60/60/24/7%52))
	local D=$((T/60/60/24%7))
	local H=$((T/60/60%24))
	local M=$((T/60%60))
	local S=$((T%60))
	[[ $Y > 0 ]] && printf '%dy ' $Y
	[[ $W > 0 ]] && printf '%dw ' $W
	[[ $D > 0 ]] && printf '%dd ' $D
	[[ $H > 0 ]] && printf '%dh ' $H
	[[ $M > 0 ]] && printf '%dm ' $M
	#[[ $D > 0 || $H > 0 || $M > 0 ]] && printf 'and '
	printf '%ds' $S
}

trim() { 
	# A Bash internals method
  	local var="$*"
  	var="${var#"${var%%[![:space:]]*}"}" # trim leading whitespace chars
  	var="${var%"${var##*[![:space:]]}"}" # trim trailing whitespace chars
	echo -n "$var"
	
	# A sed method
	#sed 's/^[[:blank:]]*//;s/[[:blank:]]*$//' <<< "$1"
	
	# An awk method 
	#awk '{$1=$1;print}' <<< $*
}

wanIP4=$(ip addr show pppoe-wan|egrep "\binet\b"|awk '{print $2}' | sed 's#/.*##')
wanIP6=$(ip addr show pppoe-wan|egrep "\binet6\b"|awk '{print $2}' | sed 's#/.*##')

if [[ $1 == "-h" ]]; then
	prv_IP="unknown"
	prv_secs=0
	while IFS="," read logtime IP reason
	do
		logtime=$(trim $logtime) 
		IP=$(trim $IP) 
		reason=$(trim $reason) 
		
	    log_secs=$(date -d"$logtime" -D"%d/%m/%Y %H:%M:%S" +"%s")
	    if (( prv_secs == 0 )); then
	    	diff_secs=""
	    	diff_dur="an unknown time"
	    else
	    	(( diff_secs = log_secs - prv_secs ))
	    	diff_dur=$(duration $diff_secs)
	    fi
	   
	   	printf '%-15s for %17s until %19s. Changed to: %-15s Reason: %s\n' "$prv_IP" "$diff_dur" "$logtime" "$IP" "$reason" 
	    
	    prv_IP=$IP
	    prv_secs=$log_secs
	done < "$logdir/$logfile"

	now_secs=$(date +'%s')
	(( diff_secs = now_secs - prv_secs ))
	diff_dur=$(duration $diff_secs)
	
	printf '%-15s for %17s until now.\n' "$wanIP" "$diff_dur"
elif [[ $1 == "-4" ]]; then
	echo $wanIP4
elif [[ $1 == "-6" ]]; then
	echo $wanIP6
else
	echo $wanIP4
	echo $wanIP6
fi
