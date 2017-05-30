#!/usr/bin/python
import json
import subprocess

p=2 # Decimal precision for humanized byte counts

def byte_fmt(num, precision=1, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return ("%3."+str(precision)+"f %s%s") % (num, unit, suffix)
        num /= 1024.0
    return ("%."+str(precision)+"f %s%s") % (num, 'Yi', suffix)

def speed_fmt(num):
    duplex = num.strip()[-1]
    if duplex == 'F':
        duplex = 'Full duplex'
        speed = num.strip()[:-1]
    elif duplex == 'H':
        duplex = 'Half duplex'
        speed = num.strip()[:-1]
    else:
        duplex = None
        speed = num.strip()

    return ("%s Mbps" % speed if duplex is None else "%s Mbps (%s)" % (speed, duplex))      

lan_devices = subprocess.check_output(["uci", "get", "network.lan.ifname"]).strip().split()

print "Interface: lan"

for dev in lan_devices:
    lan_status = json.loads(subprocess.check_output(["devstatus", dev]))

    if len(lan_devices) > 1:
        print

    print "Device: %s" % dev
    print "Up: %s" % lan_status['up']
    print "Carrier: %s" % lan_status['carrier']
    print "Speed: %s" % speed_fmt(lan_status['speed'])
    print "Received bytes: ", byte_fmt(lan_status['statistics']['rx_bytes'], precision=p)
    print "Transmitted bytes: ", byte_fmt(lan_status['statistics']['tx_bytes'], precision=p)

