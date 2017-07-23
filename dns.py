#!/usr/bin/python
#
# identify the DNS servers used on the WAN interface.

import json, subprocess, os

devnull = open(os.devnull, 'w')

def get_wan_status():
    try:
        status = subprocess.check_output(["ubus", "call", "network.interface.wan", "status"], stderr=devnull)
        return json.loads(status)
    except:
        return None

def get_owner(ip):
    try:
        return subprocess.check_output(["ip_owner", ip], stderr=devnull).strip()
    except:
        return None

wan_status = get_wan_status()
if wan_status:
    dns_servers = wan_status["dns-server"]
    print "DNS Servers on WAN interface:"
    n = 1
    for dns in dns_servers:
        owner = get_owner(dns)
        print "\tDNS %d: %s\t%s" % (n, dns, owner)
        n += 1