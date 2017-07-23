#!/usr/bin/python
#
# Fetch all the DDNS domains on this OpenWRT router and list then along with the apparent IP address.
# Or if a domain is specified then only for that domain.
# 
# A special domain "WAN" is listed for the apparent WAN address.
 
import os, subprocess, urllib, sys, argparse, json
import xml.etree.ElementTree as ET  # The API returns XML

# Configurations 
NoIP = "127.0.0.0"

# Parse arguments
parser = argparse.ArgumentParser(description='Report all DDNS domains on the router with their apparent IP addresses and the WAN address for the router',
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))

parser.add_argument('DomainName', nargs='?', help='A domain name to report on. Else reports on all domains being managed by the DDNS service in this OpenWRT router')
corj = parser.add_mutually_exclusive_group()
corj.add_argument('-c', '--csv', action='store_true', help='Print output in CSV format')
corj.add_argument('-j', '--json', action='store_true', help='Print output in JSON format')

parser.add_argument('-H', '--Header', action='store_true', help='Print header line')

#TDO: Add argument -e which reports only errors (discrepancies).

args = parser.parse_args()

def getApparentIP(domain):
    try:
        return subprocess.check_output(["dig", "+noall",  "+answer", "+short",  domain])
    except:
        return NoIP

try:
    WANIP = subprocess.check_output(["wanip"]).strip()
except:
    WANIP = NoIP

def getDomains():
    try:
        return subprocess.check_output(["ddns_domains"]).splitlines()
    except:
        return []

def getApparentIP(domain):
    try:
        return subprocess.check_output(["dig", "+noall",  "+answer", "+short",  domain]).strip()
    except:
        return NoIP
    
results = {}
maxlen = 0
if args.DomainName:
    if args.DomainName == "WAN":
        results[args.DomainName] = WANIP
    else:
        results[args.DomainName] = getRegisteredIP(args.DomainName)
    maxlen = len(args.DomainName)
else:
    Domains = getDomains()
    
    results["WAN"] = WANIP
    
    if isinstance(Domains, list):
        for Domain in Domains:
            results[Domain] = getApparentIP(Domain)
            if len(Domain) > maxlen: 
                maxlen = len(Domain)
    else:
        print >> sys.stderr, "No domains are being managed by the DDNS service"
        sys.exit()

if args.json:
    print json.dumps(results)
else:
    if args.csv:
        template = "{}, {}"
    else:
        if len(results) == 1:
            justifier = "<"
        else:
            justifier = ">"
            
        template = "{:" + justifier + str(maxlen) + "} {}"
        
    if args.Header:
        print template.format("Domain", "Apparent IP")
    for domain in results:
        print template.format(domain, results[domain])
