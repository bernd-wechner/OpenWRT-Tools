#!/bin/sh
#
# Opens a tty connection to the knot resolver.
# 
# Assumes only one instance running and connects to that.
#
# Documented here:
#
#	http://knot-resolver.readthedocs.io/en/latest/daemon.html#cli-interface
#
# Just a quick shortcut to getting at CLI for the resolver. 

tty_dir="$(uci get resolver.kresd.rundir)/tty"
tty=$(ls -1 $tty_dir | head -1)

if [[ $tty =~ ^-?[0-9]+$ && -a /proc/$tty ]]; then 
	socat - UNIX-CONNECT:$tty_dir/$tty
else
	echo "Looks like kresd is not running"
fi 