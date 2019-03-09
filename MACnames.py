#!/usr/bin/python
#
# Prints a list of MACs to Names.
# Prints a JSON dict if -j specified
# 
# Builds list by checking
# 	Active DHCP leases
# 	DHCP Configuration 
# 	Majordomo Configuration
#
# TODO: implement argparse
# TODO: implement -H option to add headers.

import os
import sys
import subprocess
import json

DHCP_LEASES = "/tmp/dhcp.leases"
devnull = open(os.devnull, 'w')

self = sys.argv[0]
option = sys.argv[1] if len(sys.argv) > 1 else None

def get_DHCP_leases():
	leases = {}
	with open(DHCP_LEASES) as lease_file:
		for line in lease_file:
			fields = line.split()
			MAC = fields[1].upper()
			name = fields[3]
			leases[MAC] = name
	return leases

def has_DHCP_conf(i):
	return 0==subprocess.call(["uci", "get", "dhcp.@host[%d]" % i], stdout=devnull, stderr=devnull)

def get_DHCP_conf(i):
	try:
		name = subprocess.check_output(["uci", "get", "dhcp.@host[%d].name" % i], stderr=devnull).strip()
	except:
		name = None
			
	try:
		MAC = subprocess.check_output(["uci", "get", "dhcp.@host[%d].mac" % i], stderr=devnull).strip().upper()
	except:
		MAC = None

	return (name, MAC)

def get_DHCP_confs():
	conf = {}
	i=0
	while has_DHCP_conf(i):
		(name, MAC) = get_DHCP_conf(i)
		if not MAC is None: 
			conf[MAC] = name
		i+=1	
	return conf

def has_MajorDomo_conf(i):
	return 0==subprocess.call(["uci", "get", "majordomo.@static_name[%d]" % i], stdout=devnull, stderr=devnull)

def get_MajorDomo_conf(i):
	try:
		name = subprocess.check_output(["uci", "get", "majordomo.@static_name[%d].name" % i], stderr=devnull).strip()
	except:
		name = None
			
	try:
		MAC = subprocess.check_output(["uci", "get", "majordomo.@static_name[%d].mac" % i], stderr=devnull).strip().upper()
	except:
		MAC = None

	return (name, MAC)

def get_MajorDomo_confs():
	conf = {}
	i=0
	while has_MajorDomo_conf(i):
		(name, MAC) = get_MajorDomo_conf(i)
		if not MAC is None: 
			conf[MAC] = name
		i+=1	
	return conf

# Start with the known DHCP leases 
result = get_DHCP_leases()

# Augment with any DHCP conf info
conf = get_DHCP_confs()
for MAC in conf:
	if not MAC in result:
		result[MAC] = conf[MAC]

# Augment with any MajorDomo conf info
conf = get_MajorDomo_confs()
for MAC in conf:
	if not MAC in result:
		result[MAC] = conf[MAC]
		
if option == "-j":
	print json.dumps(result)
else:
	for MAC in sorted(result.iterkeys()):
		print MAC, result[MAC]
		