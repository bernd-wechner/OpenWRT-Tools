#!/usr/bin/python
import json
import os, subprocess
from datetime import datetime, timedelta

devnull = open(os.devnull, 'w')

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

def duration_formatted(seconds, suffixes=['y','w','d','h','m','s'], add_s=False, separator=' '):
    """
    Takes an amount of seconds (as an into or float) and turns it into a human-readable amount of time.
    """
    # the formatted time string to be returned
    time = []
 
    # the pieces of time to iterate over (days, hours, minutes, etc)
    # - the first piece in each tuple is the suffix (d, h, w)
    # - the second piece is the length in seconds (a day is 60s * 60m * 24h)
    parts = [(suffixes[0], 60 * 60 * 24 * 7 * 52),
             (suffixes[1], 60 * 60 * 24 * 7),
             (suffixes[2], 60 * 60 * 24),
             (suffixes[3], 60 * 60),
             (suffixes[4], 60),
             (suffixes[5], 1)]
 
    # for each time piece, grab the value and remaining seconds, 
    # and add it to the time string
    for suffix, length in parts:
        if length == 1:
            value = seconds
        else:
            value = int(seconds / length)
        if value > 0 or length == 1:
            if length == 1:
                if isinstance(value, int):
                    svalue = "{}".format(value)
                else:
                    svalue = "{:.2f}".format(value)                
            else:
                svalue = str(int(value))
                seconds = seconds % length       # Remove the part we are printing now
                
            time.append('%s%s' % (svalue, (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
 
    return separator.join(time)

def get_wan_status():
    try:
        status = subprocess.check_output(["ubus", "call", "network.interface.wan", "status"], stderr=devnull)
        return json.loads(status)
    except:
        return None     

def get_dev_status(device):
    try:
        status = subprocess.check_output(["devstatus", device])
        return json.loads(status)
    except:
        return None     

def get_wan_devices():
    try:
        return subprocess.check_output(["uci", "get", "network.wan.ifname"]).strip().split()
    except:
        return []     

wan_devices = get_wan_devices()
wan_status = get_wan_status()

print "Interface: wan"

for device in wan_devices:
    dev_status = get_dev_status(device)

    if len(wan_devices) > 1:
        print
        
    print "Device: %s" % device
    print "Up: %s" % dev_status['up']
    
    if dev_status['up'] and wan_status:
        up_time = datetime.now() - timedelta(seconds=wan_status["uptime"])
        print "  IP: %s" % wan_status["ipv4-address"][0]["address"]
        print "  Up for: %s" % duration_formatted(wan_status["uptime"])
        print "  Up since: %s" % datetime.strftime(up_time, "%c")
    
    print "Carrier: %s" % dev_status['carrier']
    print "Speed: %s" % speed_fmt(dev_status['speed'])
    print "Received bytes: ", byte_fmt(dev_status['statistics']['rx_bytes'], precision=p)
    print "Transmitted bytes: ", byte_fmt(dev_status['statistics']['tx_bytes'], precision=p)

