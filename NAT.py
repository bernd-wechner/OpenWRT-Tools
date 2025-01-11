#!/usr/bin/python
#
# A quick way to see all incoming and outgoing NAT translations.
#
# Important because LuCI will show us the static NAT configurations, but not the dynamic NAT routes,
# that arise whan an outward bound TCP connection is formed. This is especially interesting with
# IoT devices on the LAN to see what incoming traffic they draw.
#
# Draws on conntrack, the lnimux utility that tracks linux kernel netwoork connections.

import os
import json
import subprocess
import argparse
import pickle

parser = argparse.ArgumentParser(description='Show NAT connection mappings.',
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))
parser.add_argument('-i', '--Inward', action='store_true', help='Show inward bound mappings.')
parser.add_argument('-o', '--Outward', action='store_true', help='Show outward bound mappings')

args = parser.parse_args()

devnull = open(os.devnull, 'w')

connections = subprocess.check_output("conntrack -p tcp -L".split(), stderr=devnull).splitlines()
WAN_IP = subprocess.check_output("wanip -4".split(), stderr=devnull).strip()
LAN_names = json.loads(subprocess.check_output(["IPnames", "-j"], stderr=devnull))

name_cache = {}
name_cache_file = "/tmp/name_cache.pickle"

# Load a name cahce if we have one
try:
    with open(name_cache_file) as f:
        name_cache = pickle.load(f)
except:
    pass  # No worries, start with an empty cache


def Name(IP):
    # Only use the name cache for the costly dig lookup, local LAN names and the WANIP substution
    # are cheap and we can look them up live. Reverse DNS is slow and hence we want to prefer a
    # cache. Ideally we would have the DNS (kresd in my case) keep a cache of names resolved that
    # could consult to have a better chance at seeing the actual name used by a client in forming
    # the connection
    if IP in LAN_names:
        name_cache[IP] = LAN_names[IP]
    elif IP == WAN_IP:
        name_cache[IP] = "thumbs.place"
    elif IP in name_cache:
        pass
    else:
        dig = subprocess.check_output("dig +short -x {}".format(IP).split(), stderr=devnull).strip()[:-1]
        if dig:
            name_cache[IP] = dig
        else:
            name_cache[IP] = "unknown"

    return name_cache[IP]


Connections = []

for c in connections:
    fields = c.split()

    # A sample line from conntrack -L:
    #   00  tcp
    #   01  6
    #   02  7411
    #   03  ESTABLISHED
    #   04  src=192.168.0.206
    #   05  dst=13.56.143.44
    #   06  sport=30291
    #   07  dport=443
    #   08  packets=2717
    #   09  bytes=193825
    #   10  src=13.56.143.44
    #   11  dst=203.63.3.28
    #   12  sport=443
    #   13  dport=30291
    #   14  packets=1402
    #   15  bytes=142342
    #   16  [ASSURED]
    #   17  mark=0
    #   18  use=1

    status = fields[3]

    OB_src_IP = fields[4][4:]
    OB_dst_IP = fields[5][4:]
    OB_src_Port = fields[6][6:]
    OB_dst_Port = fields[7][6:]

    OB_src_Name = Name(OB_src_IP)
    OB_dst_Name = Name(OB_dst_IP)

    IB_src_IP = fields[10][4:]
    IB_dst_IP = fields[11][4:]
    IB_src_Port = fields[12][6:]
    IB_dst_Port = fields[13][6:]

    IB_src_Name = Name(IB_src_IP)
    IB_dst_Name = Name(IB_dst_IP)

    if status == "ESTABLISHED":
        # Store summary info as a 4 tuple of 3 tuples
        # Each 3 tuple being IP, Name, Port
        # The 4 tuple being OB source, OB destination, IB source, IB destination
        Connections.append(((OB_src_IP, OB_src_Name, OB_src_Port),
                            (OB_dst_IP, OB_dst_Name, OB_dst_Port),
                            (IB_src_IP, IB_src_Name, IB_src_Port),
                            (IB_dst_IP, IB_dst_Name, IB_dst_Port)))

CONNECTIONS = []

for c in Connections:
    OB_key = c[0][0]
    OB_src = "{1} ({0}):{2}".format(c[0][0], c[0][1], c[0][2])
    OB_dst = "{1} ({0}):{2}".format(c[1][0], c[1][1], c[1][2])

    IB_key = c[2][0]
    IB_src = "{1} ({0}):{2}".format(c[2][0], c[2][1], c[2][2])
    IB_dst = "{1} ({0}):{2}".format(c[3][0], c[3][1], c[3][2])

    # Store a formatted (ordered) summary as a 6 tuple (2 sort keys and 4 formatted strings)
    CONNECTIONS.append((OB_key, IB_key, OB_src, OB_dst, IB_src, IB_dst))

# Print Outward Bound connections first
if args.Outward:
    for c in sorted(CONNECTIONS, key=lambda conn: (conn[0], conn[1])):
        print "{} -> {}".format(c[2], c[3])

# Then Inward Bound connections
if args.Inward:
    for c in sorted(CONNECTIONS, key=lambda conn: (conn[2], conn[3])):
        print "{} -> {}".format(c[4], c[5])

# Save the name cache
with open(name_cache_file, 'wb') as f:
    pickle.dump(name_cache, f)
