#!/usr/bin/python
#
# Accepts a MAC or IP address as an argument and tries to find a name that is mapped to that
# MAC or IP on the current router. 
#
# Uses MACnames -j and IPnames -j and dig as needed: 

import re
import os
import sys
import subprocess
import socket
import json

devnull = open(os.devnull, 'w')

def isMAC(address):
	return re.match("[0-9A-F]{2}([-:])[0-9A-F]{2}(\\1[0-9A-F]{2}){4}$", address.upper())

def isIP(address):
	try:
		socket.inet_aton(address)
		return True
	except socket.error:
		if socket.has_ipv6:
			try:
				socket.inet_pton(socket.AF_INET6, address)
				return True
			except:
				return False
		else:
			return False	

self = sys.argv[0]
address = sys.argv[1].upper() if len(sys.argv) > 1 else None

if isMAC(address):
	names = json.loads(subprocess.check_output(["MACnames", "-j"], stderr=devnull))
	if address in names:
		print names[address]
elif isIP(address):
	names = json.loads(subprocess.check_output(["IPnames", "-j"], stderr=devnull))
	if address in names:
		print names[address]
	else:
		name = subprocess.check_output(["dig", "+short", "-x", address], stderr=devnull).replace(".\n","\n").strip()
		print name
else:
	print "Must specify a MAC or IP address"
	sys.exit(1)