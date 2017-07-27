#!/bin/bash
#
# List Turris Omnia notifications.
#
# The Foris Web interfce currently doesn't show whether an email was sent or not
#
# Desireable to quickly see whether an email was sent or not nonexisting notifications for
# the simple purpose of dspotting any mailer issues (did the mail actually arrive?) 

ndir="/tmp/user_notify"
FMT='%-29s %-8s %-8s %s\n'

count=0
header=$(printf "$FMT" 'Date/time' 'Severity' 'Emailed?' 'First line of message')
output=("$header")

for d in $ndir/*
do
	if [ -d "$d" ] ; then
   		severity=$(cat "$d/severity")
   		[ -f "$d/sent_by_email" ] && emailed="True" || emailed="False"
   		message=$(head -1 "$d/message_en")
   		msgtime=$(date -r $d)
   		output+=("$(printf "$FMT" "$msgtime" "$severity" "$emailed" "$message")")
   		let count+=1
   	fi
done

if (( $count == 0 )); then
	printf 'No messages\n'
else
	(( count > 1 )) && s="s" || s=""
	printf '%s message%s active.\n\n' $count $s
	printf '%s\n' "${output[@]}"
fi

