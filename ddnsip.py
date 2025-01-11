#!/usr/bin/python
#
# Fetch all the DDNS domains on this OpenWRT router and list them along with the apparent IP address.
# Or if a domain is specified then only for that domain.
# 
# A special domain "WAN" is listed for the apparent WAN address.
 
import os, subprocess, sys, argparse, json

# Configurations
web_header = ["NameCheap", "Cerberus", "AlwaysData"]
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

Worw = parser.add_mutually_exclusive_group()
Worw.add_argument('-w', '--Web', action='store_true', help='Use a webservice to improve results but only if there\'s a WAN IP/Apparent IP discrepancy.')
Worw.add_argument('-W', '--WebForce', action='store_true', help='Use a webservice to improve results')

parser.add_argument('-H', '--Header', action='store_true', help='Print header line')
parser.add_argument('-n', '--Notify', action='store_true', help='Notify administrator of results')

Eore = parser.add_mutually_exclusive_group()
Eore.add_argument('-e', '--ErrorReport', action='store_true', help='Report only errors')
Eore.add_argument('-E', '--EmphasizeErrors', action='store_true', help='Emphasizes errors in the report')

args = parser.parse_args()

try:
    WANIP = subprocess.check_output(["wanip", "-4"]).strip()
except:
    WANIP = NoIP

def getDomains():
    try:
        return subprocess.check_output(["ddns_domains"]).splitlines()
    except:
        return []

def getApparentIP(domain):
    try:
        # for CNAME records (commonly subdomains) dig retrusn two lines and the IP is on the second
        return subprocess.check_output(["dig", "+noall",  "+answer", "+short",  domain]).strip().split("\n")[-1]
    except:
        return NoIP

def getWebData():
    try:
        return json.loads(subprocess.check_output(["ddns_web", "-j"]).strip())
    except:
        return None

def notify(status, message):
    try:
        subprocess.check_call(["create_notification", "-s", status, "", message], stderr=devnull, stdout=devnull)
        subprocess.check_call(["notifier"], stderr=devnull, stdout=devnull)
    except:
        return "Error: Notification failed."

results = {}
errors = 0
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
            # We have to loop over all the hosts here
            # And it's then Host.Domain
            
            IP = getApparentIP(Domain)
            if IP != WANIP:
                errors += 1

            if args.EmphasizeErrors and IP != WANIP:
                Domain = Domain.upper()
            
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

# Get web data if requested (this can be a bit slow so is not on by default)
results_web = None
if args.WebForce and args.ErrorReport and errors == 0:
    args.WebForce = False  
if args.WebForce or (args.Web and errors > 0):
    results_web = getWebData()

# Now augment the results with web service sourced data if we have it
if not results_web is None:
    for Domain in results:
        LowerDomain = Domain.lower()
        if Domain == "WAN":
            IP_registered = ""
            IP_apparent = ""
        elif LowerDomain in results_web:
            IP_registered = results_web[LowerDomain][0]
            IP_apparent = results_web[LowerDomain][1]
        else:
            IP_registered = "unknown"
            IP_apparent = "unknown"
        
        if args.ErrorReport:
            results[Domain] = (IP_registered, results[Domain][0], IP_apparent, WANIP)
        else:
            results[Domain] = (IP_registered, results[Domain][0], IP_apparent)

if args.json:
    print json.dumps(results)
else:
    if args.csv:
        template = "{}, {}"
        if not results_web is None:
            template += ", {}, {}"
        if args.ErrorReport:
            template += ", {}"
    else:
        if len(results) == 1:
            justifier = "<"
        else:
            justifier = ">"
            
        template = "{:" + justifier + str(maxlen) + "} {:<15}"
        if not results_web is None:
            template += " {:<15} {:<15}"
        if args.ErrorReport:
            template += " {:<15}"
    
    if args.Header and args.ErrorReport and len(results)> 0:
        output = ["Dynamic DNS update errors detected.\n"]
        output += ["Diagnostics tools can be found at: http://thumbs-place.alwaysdata.net/ddns\n"]
    else:
        output = []
    
    if args.Header:
        if not results_web is None:
            IPheader = [web_header[0]+" IP", web_header[1]+" IP", web_header[2]+" IP"]
        else:
            IPheader = ["Apparent IP"]
            
        if args.ErrorReport:
            IPheader += ["Expected IP"]
            
        if errors > 0 or not args.ErrorReport:
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
