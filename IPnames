#!/usr/bin/python
#
# Prints a list of IPs to Names.
# Prints a JSON dict if -j specified
# 
# Builds list by checking
# 	Active DHCP leases
# 	DHCP Configuration 

import os
import sys
import subprocess
import json
import socket

DHCP_LEASES = "/tmp/dhcp.leases"
devnull = open(os.devnull, 'w')

self = sys.argv[0]
option = sys.argv[1] if len(sys.argv) > 1 else None

def get_DHCP_leases():
	leases = {}
	with open(DHCP_LEASES) as lease_file:
		for line in lease_file:
			fields = line.split()
			IP = fields[2]
			name = fields[3]
			leases[IP] = name
	return leases

def has_DHCP_conf(i):
	return 0==subprocess.call(["uci", "get", "dhcp.@host[%d]" % i], stdout=devnull, stderr=devnull)

def get_DHCP_conf(i):
	try:
		name = subprocess.check_output(["uci", "get", "dhcp.@host[%d].name" % i], stderr=devnull).strip()
	except:
		name = None
			
	try:
		IP = subprocess.check_output(["uci", "get", "dhcp.@host[%d].ip" % i], stderr=devnull).strip()
	except:
		IP = None

	return (name, IP)

def get_DHCP_confs():
	conf = {}
	i=0
	while has_DHCP_conf(i):
		(name, IP) = get_DHCP_conf(i)
		if not IP is None: 
			conf[IP] = name
		i+=1	
	return conf

# Start with the known DHCP leases 
result = get_DHCP_leases()

# Augment with any DHCP conf info
conf = get_DHCP_confs()
for IP in conf:
	if not IP in result:
		result[IP] = conf[IP]
	
if option == "-j":
	print json.dumps(result)
else:
	for IP in sorted(result.iterkeys(), key=lambda item: socket.inet_aton(item)):
		print IP, result[IP]
		