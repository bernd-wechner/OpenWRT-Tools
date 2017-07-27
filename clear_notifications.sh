#!/bin/bash
#
# Clear Turris Omnia notifications.
#
# The Foris Web interfce currently doesn't support this:
#
# 	https://github.com/CZ-NIC/foris/issues/9
# 
# SO a CLI method is desireable. And handy regardless.

ndir="/tmp/user_notify"
tdir="/tmp/trash"

mkdir -p $tdir

messages=$(ls $ndir)

if [[ $messages != "" ]]; then
	mv $ndir/* $tdir
fi
