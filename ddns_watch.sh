#!/bin/bash
# Watch the net for propagation of a DDNS IP
# This is ordinarily run after a DDNS IP update to watch propagation of the newly updated DDNS IP
# Outputs two times measured in seconds since epoch being:
# 	The time the first DDNS domain reflected the current WAN IP
#	The time all DDNS domain reflected the current WAN IP
#
# Depends on:
#
#	ddnsip -c			- which should accompany this script, and produces a list of DDNS managed domains and their dig identified IP addresses.
#	wanip				- ddnsip depends on this utility, which prints the current WAN IP of the router we're running on
#	ddns_domains		- ddnsip depends on this utility, which prionts a list of domains under DDNS management that should point to this router
#
# TODO: Integrate this with log_wanip.sh and index.php to run on ifup, log the results of watch and notify of the results.  

# Allow one instance only of this script to run. 
# If a new instance is invoked, it should exit silently.
# This script watches the WAN IP and if it changes resets its ppropagation watching timers
# Meaning until a stable propagation is seen and it exits, there is zero need for a new
# instance to start up and start watching the DDNS prpopagation.
SCRIPTNAME=$(basename $0)
LOCK=/var/run/${SCRIPTNAME}.lock
if [ -f "${LOCK}" ]; then
	read PID < "${LOCK}"
	if [ -e /proc/$PID ]; then
		# An instance of this shell is running right now.  
		exit 1
	else 
		# No process with the PID in the lock file is running, 
		# so it looks like a ghost lock file and we can just overrite it and carry on
		echo $$ > "${LOCK}"
	fi
else
	echo $$ > "${LOCK}"
fi

# Some basic declarations
sleep_time=1	# seconds between propagation checks

declare -A IP	# A hashed array of IP addresses keyed on domain 

printarr() { declare -n __p="$1"; for k in "${!__p[@]}"; do printf "%s=%s\n" "$k" "${__p[$k]}" ; done ;  }  

time_start=$(date +%s)
time_first=0
time_last=0

WANIP=$(wanip)

while true; do
	# Fetch the DDNS domain names and apparent IPs
	while IFS=', ' read domain ip; do
	    IP["${domain//[[:space:]]/}"]="${ip//[[:space:]]/}"
	done <<< $(ddnsip -c)

	# Squirrel away the reported WAN IP
	# ddnsip returns a faux domain called WAN and lists the current WAN IP of the router in that
	OLD_WANIP=$WANIP
	WANIP=${IP[WAN]}
	unset IP[WAN]

	# Reset timers if WAN IP has changed since we started watching
	# This implies a DDNS IP update has happened since we started watching
	if [[ $WANIP != $OLD_WANIP ]]; then
		time_start=$(date +%s)
		time_first=0
		time_last=0
	fi

	#Debugging output
	#echo	
	#echo WAN IP is $WANIP
	#printarr IP

	# Count how many DDNS domain IPs match the current WAN IP
	count=${#IP[@]}
	matched=0
	for domain in "${!IP[@]}"; do
		ip=${IP[$domain]}
				
		if [[ $ip == $WANIP ]]; then ((matched++)); fi
	done

	if (( $time_first == 0 && $matched > 0 )); then 
		time_first=$(date +%s) 
	fi
		
	if (( $matched == $count )); then 
		time_last=$(date +%s)
		break
	else
		sleep $sleep_time
	fi
done

#Debugging output
#echo start=$time_start first=$time_first last=$time_last
#echo start=$(date -d @$time_start) first=$(date -d @$time_first) last=$(date -d @$time_last)

# TODO: Output results
# Consider: one line at start, one line at first, one line when done, summary of times line.
# Consider args to select lines, and format.
# Result should be notified as well either here or by caller, decide (notify meaning, an Omnia notification and email).

if [ -f "${LOCK}" ]; then
    rm "${LOCK}"
fi

