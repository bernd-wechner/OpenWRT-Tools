#!/bin/bash
# the whois utility isn't available on OpenWRT alas. Forsooth.
#
# here's an on-line API that will process up to 50 queries a day from one IP.
 
curl -s "http://api.hackertarget.com/whois/?q=$1"