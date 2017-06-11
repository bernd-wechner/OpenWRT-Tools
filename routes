#!/usr/bin/python
#
# Prints /proc/net/arp, prepended with a column naming the device if possible,
# Uses MACnames -j and IPnames -j to build reference tables for names
#
# This was an effort to reproduce LuCI's Routes page with a CLI command.
# It's not quite the same though. /proc/net/arp has some entries LuCI doesn'y display.
#
# Accepts one argument:
# -i  sort by IP
# -m  sort by MAC
# -n  sort by name
# default is unsorted
#
# TODO: should really take multiple sort options, first, secondary and teriary sort keys. 

import os
import sys
import json
import fileinput
import subprocess
import socket

self = sys.argv[0]
option = sys.argv[1] if len(sys.argv) > 1 else None

ARP = "/proc/net/arp"

devnull = open(os.devnull, 'w')

MACnames = json.loads(subprocess.check_output(["MACnames", "-j"], stderr=devnull))
IPnames = json.loads(subprocess.check_output(["IPnames", "-j"], stderr=devnull))

result = {}

for line in fileinput.input(ARP):
	if fileinput.isfirstline():
		header = "%-25s %s" % ("HW name", line.strip())
	else:
		fields = line.split()
		IP = fields[0]
		MAC = fields[3].upper()
		
		if MAC in MACnames:
			name = MACnames[MAC]
		elif IP in IPnames:
			name = IPnames[IP]
		else:
			name = "<unknown>"
		
		if option == "-i":
			key = IP
		elif option == "-m":
			key = MAC
		elif option == "-n":
			key = name
		else:
			key = fileinput.filelineno()
		
		while key in result:
			key += "."
		
		result[key] = "%-25s %s" % (name, line.strip())

print header

# Collect some summary info
count = len(result)
# TODO: Count of each Flags category
# TODO: Count of entries with missing MAC (MAC is 00:00:00:00:00:00
# TODO: COunt of entries that no name was found for

# Sort the results is requested
if option == "-i":
	keys = sorted(result.iterkeys(), key=lambda item: socket.inet_aton(item))
else:
	keys = sorted(result.iterkeys())

for key in keys:
	print result[key]

print "%d total routes." % count
