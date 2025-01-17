#!/usr/bin/python
#
# Get the namecheap configured dynamic IP address for a given users domains.
# 
# Ideally this would be simple with a URL like this:
#     http://dynamicdns.park-your-domain.com/update?host=%40&[DOMAIN]&password=[PASSWORD]
# But alas, that updates the IP with the WAN IP alas does not just report it. 
# The WAN IP can be fetched with:
#     http://dynamicdns.park-your-domain.com/getip
# But the configured IP for Dynamic DNS domains cannot be checked without setting it 
# (its is reported when set).
#
# Not a crisis per se. But not a check either.
#
# So I filed a support ticket to implement such a feature:
#
#     https://support.namecheap.com/index.php?/Tickets/Ticket/View/WWL-151-97492
#
# But in the mean time (with no guarantee it will be implemented) namecheap pointed me to their API. 
# It's do-able with the API but there's a catch. The API is overkill, it's designed for managing the 
# domains and targeted at businesses with customers. To wit there are some hurdles:
#
# 1) Access must be approved, and will only be approved if you've tested your tools in the sandbox they provide.
# 2) You can only get access if you have 20 domains or more registered with them or spent $50 or more with them 
#    in the past two years. Not a huge hurdle but if you haven't spent $50 you may need to access the API.
# 3) You need to enable the API on your account and whitelist any IPs from which you access it explicitly.
 
import os, subprocess, urllib, sys, argparse, json
import xml.etree.ElementTree as ET  # The API returns XML

# Configurations 
AuthFile = "~/.auth/namecheap.auth"
APIURL = "https://api.namecheap.com/xml.response"
XMLprefix = "{http://api.namecheap.com/xml.response}"
NoIP = "127.0.0.0"

# Parse arguments
parser = argparse.ArgumentParser(description='Report registered IP address(es) for Namecheap registered Dynamic Domain Names.',
                                 epilog = "Requires that you have valid authorization details in {}.".format(AuthFile) +
                                          "This is a simple text file with two lines, username=USERNAME and APIkey=APIKEY.",
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))

parser.add_argument('DomainName', nargs='?', help='A domain name to report on. Else reports on all domains registered to the user found in ' + AuthFile)
corj = parser.add_mutually_exclusive_group()
corj.add_argument('-c', '--csv', action='store_true', help='Print output in CSV format')
corj.add_argument('-j', '--json', action='store_true', help='Print output in JSON format')

parser.add_argument('-H', '--Header', action='store_true', help='Print header line')

args = parser.parse_args()

def readAuth(file):
    auth = {}
    try:
        with open(os.path.expanduser(file)) as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                tokens = line.split('=')
                if len(tokens) == 2:
                    auth[tokens[0].strip()] = tokens[1].strip()
    except:
        print >> sys.stderr, "Cannot open authorization file: {}".format(file)
        sys.exit()
        
    return auth

try:
    ClientIP = subprocess.check_output(["wanip"])
except:
    ClientIP = NoIP

# Read authorization file
auth = readAuth(AuthFile)
username = auth["username"] 
APIkey = auth["APIkey"] 

def APIglobals():
    return "?ApiUser={}&UserName={}&ApiKey={}&ClientIP={}".format(username, username, APIkey, ClientIP)
    
def getDomains():
    Names = []
    URL = APIURL + APIglobals() + "&Command=namecheap.domains.getList"
    response = urllib.urlopen(URL).read()
    ApiResponse = ET.fromstring(response)
    if ApiResponse.attrib["Status"] == "OK":
        CommandResponse = ApiResponse.find(XMLprefix+"CommandResponse")
        DomainGetListResult = CommandResponse.find(XMLprefix+"DomainGetListResult")
        Domains = DomainGetListResult.findall(XMLprefix+"Domain")
        
        for Domain in Domains:
            Name = Domain.attrib["Name"]
            Names += [Name]
            
        return Names
    elif ApiResponse.attrib["Status"] == "ERROR":
        Errors = ApiResponse.find(XMLprefix+"Errors")
        print >> sys.stderr, "Errors fetching domain names:"
        for Error in Errors.findall(XMLprefix+"Error"):
            print >> sys.stderr, Error.text
        sys.exit()             
    else:
        return None

def getApparentIP(domain):
    try:
        return subprocess.check_output(["dig", "+noall",  "+answer", "+short",  domain])
    except:
        return NoIP
    
def getRegisteredIP(domain):
    global ClientIP
    if ClientIP == NoIP:
        ClientIP = getApparentIP(domain)
        
    parts = domain.split('.')
    TLD = parts[-1]
    SLD = parts[-2]
    URL = APIURL + APIglobals() + "&Command=namecheap.domains.dns.getHosts&SLD={}&TLD={}".format(SLD, TLD)
    response = urllib.urlopen(URL).read()
    ApiResponse = ET.fromstring(response)
    
    if ApiResponse.attrib["Status"] == "OK":
        CommandResponse = ApiResponse.find(XMLprefix+"CommandResponse")
        DomainDNSGetHostsResult = CommandResponse.find(XMLprefix+"DomainDNSGetHostsResult")
        hosts = DomainDNSGetHostsResult.findall(XMLprefix+"host")
        
        for host in hosts:
            Type = host.attrib["Type"]
            Name = host.attrib["Name"]
            Address = host.attrib["Address"]
            IsDDNSEnabled = host.attrib["IsDDNSEnabled"]
            if Type == "A" and IsDDNSEnabled == "true":
                return Address
    elif ApiResponse.attrib["Status"] == "ERROR":
        try:
            Errors = ApiResponse.find(XMLprefix+"Errors")
            lstErrorTxt = []
            for Error in Errors.findall(XMLprefix+"Error"):
                lstErrorTxt += [Error.text]
            return ", ".join(lstErrorTxt)
        except:
            print >> sys.stderr, "Unable to parse Error response:\n" + response
            return None
    else:
        return None

results = {}
maxlen = 0
if args.DomainName:
    results[args.DomainName] = getRegisteredIP(args.DomainName)
    maxlen = len(args.DomainName)
else:
    Domains = getDomains()
    
    if isinstance(Domains, list):
        for Domain in Domains:
            results[Domain] = getRegisteredIP(Domain)
            if len(Domain) > maxlen: 
                maxlen = len(Domain)
    else:
        print >> sys.stderr, "No domains registered"
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
        print template.format("Domain", "Registered IP")
    for domain in results:
        print template.format(domain, results[domain])   
