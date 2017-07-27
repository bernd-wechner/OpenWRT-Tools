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
devnull = open(os.devnull, 'w')

# Parse arguments
parser = argparse.ArgumentParser(description='Report all DDNS domains on the router with their apparent IP addresses and the WAN address for the router',
                                 epilog="Uses the Turris Omnia notification system for the -n option." +
                                        "The web service used by -w needs to be configured and is provided by index.php, default.css and ncdip in thie accompanying toolset.",
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=25))

parser.add_argument('DomainName', nargs='?', help='A domain name to report on. Else reports on all domains being managed by the DDNS service in this OpenWRT router')
corj = parser.add_mutually_exclusive_group()
corj.add_argument('-c', '--csv', action='store_true', help='Print output in CSV format')
corj.add_argument('-j', '--json', action='store_true', help='Print output in JSON format')

parser.add_argument('-H', '--Header', action='store_true', help='Print header line')
parser.add_argument('-e', '--ErrorReport', action='store_true', help='Produce an error report')
parser.add_argument('-n', '--Notify', action='store_true', help='Notify administrator of results')
parser.add_argument('-w', '--Web', action='store_true', help='Use a webservice to improve results')

#TDO: Add argument -e which reports only errors (discrepancies).

args = parser.parse_args()

try:
    WANIP = subprocess.check_output(["wanip"]).strip() + "dirty"
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

def notify(status, message):
    try:
        subprocess.check_call(["create_notification", "-s", status, "", message], stderr=devnull, stdout=devnull)
        subprocess.check_call(["notifier"], stderr=devnull, stdout=devnull)
    except:
        return "Error: Notification failed."
    
results = {}
maxlen = 0
if args.DomainName:
    if args.DomainName == "WAN":
        results[args.DomainName] = WANIP
    else:
        results[args.DomainName] = getApparentIP(args.DomainName)
    maxlen = len(args.DomainName)
else:
    Domains = getDomains()
    
    if not args.ErrorReport:
        results["WAN"] = (WANIP,)
    
    if isinstance(Domains, list):
        for Domain in Domains:
            IP = getApparentIP(Domain)
            
            if args.ErrorReport:
                if IP != WANIP:
                    results[Domain] = (IP, WANIP)
            else:
                results[Domain] = (IP,)
                
            if Domain in results:
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
        if args.ErrorReport:
            template += ", {}"
    else:
        if len(results) == 1:
            justifier = "<"
        else:
            justifier = ">"
            
        template = "{:" + justifier + str(maxlen) + "} {:<15}"
        if args.ErrorReport:
            template += " {}"
    
    if args.Header and args.ErrorReport and len(results)> 0:
        output = ["Dynamic DNS update errors detected.\n"]
    else:
        output = []
    
    if args.Header:
        IPheader = ["Apparent IP"]
        if args.ErrorReport:
            IPheader += ["Expected IP"]
            
        if not args.ErrorReport or len(results) > 0:
            output += [template.format("Domain", *IPheader)]
        
    for domain in results:
        output += [template.format(domain, *results[domain])]
    
    if len(output) > 0:    
        if args.Notify:
            if args.ErrorReport:
                status = "error"
            else:
                status = "news"
            notify(status, "\n".join(output))
        else:
            for line in output:
                print line
        
