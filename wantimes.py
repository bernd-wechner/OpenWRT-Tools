#!/usr/bin/python
import re, json, subprocess, os
from datetime import datetime, timedelta

devnull = open(os.devnull, 'w')

# A sample message stream of the sort we want to summarise
#2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' has link connectivity 
#2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' is setting up now
#2017-05-29T00:09:43+10:00 notice netifd[]: Network device 'pppoe-wan' link is up
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is enabled
#2017-05-29T00:09:43+10:00 notice netifd[]: Network alias 'pppoe-wan' link is up
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' has link connectivity 
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is setting up now
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan' is now up
#2017-05-29T00:09:43+10:00 notice firewall[]: Reloading firewall due to ifup of wan (pppoe-wan)
#2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' has link connectivity 
#2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' is setting up now
#2017-05-29T00:09:43+10:00 notice netifd[]: Network device 'pppoe-wan' link is up
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is enabled
#2017-05-29T00:09:43+10:00 notice netifd[]: Network alias 'pppoe-wan' link is up
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' has link connectivity 
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is setting up now
#2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan' is now up
#2017-05-29T00:09:43+10:00 notice firewall[]: Reloading firewall due to ifup of wan (pppoe-wan)
#2017-05-29T00:09:54+10:00 notice netifd[]: Interface 'wan6' is now down
#2017-05-29T00:09:54+10:00 notice netifd[]: Interface 'wan6' is disabled
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan6' has link connectivity loss
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is now down
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is disabled
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is enabled
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is setting up now
#2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' has link connectivity loss
#2017-05-29T05:32:33+10:00 notice netifd[]: Interface 'wan' has link connectivity 
#2017-05-29T05:32:33+10:00 notice netifd[]: Interface 'wan' is setting up now
#2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' is now down
#2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' is disabled
#2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' has link connectivity loss
#2017-05-29T05:34:15+10:00 notice netifd[]: Interface 'wan' is enabled
#2017-05-29T05:34:19+10:00 notice netifd[]: Interface 'wan' has link connectivity 
#2017-05-29T05:34:19+10:00 notice netifd[]: Interface 'wan' is setting up now

def displaymatch(match):
    if match is None:
        return None
    return '<Match: %r, groups=%r>' % (match.group(), match.groups())

def add_time_offet(time, offset):
    # offset is in log format of [+-]hh:mm
    match = re.match(r"(?P<dir>[+-])(?P<hours>\d\d):(?P<mins>\d\d)", offset) 
    delta = timedelta(hours=int(match.group("hours")), minutes=int(match.group("mins")))
    if match.group("dir") == "+":
        return time + delta
    else:
        return time - delta

def get_wan_status():
    try:
        status = subprocess.check_output(["ubus", "call", "network.interface.wan", "status"], stderr=devnull)
        return json.loads(status)
    except:
        return None

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
    
log_pattern = r"(?P<time>[0-9T:+-]*)\s+(?P<type>\w*)\s+(?P<process>[\w./_-]*)\[(?P<pid>\d*)\]: (?P<message>.*)"

# First report the known up time
wan_status = get_wan_status()
if wan_status:
    up_time = datetime.now() - timedelta(seconds=wan_status["uptime"])
    print "Link has been up for %s since %s (from current WAN status)" % (duration_formatted(wan_status["uptime"]), datetime.strftime(up_time, "%c"))


# Then scan the messages log for down and up reports
went_up = None
went_down = None

with open("/var/log/messages") as log_file:
    for line in log_file:
        match = re.match(log_pattern, line)
        if not match is None:
            off_pattern = r'([+-]\d\d:\d\d$)'
            off_time = re.search(off_pattern, match.group("time")).group(1)
            log_time = re.sub(off_pattern, '', match.group("time"))
            log_time = datetime.strptime(log_time, "%Y-%m-%dT%H:%M:%S")
            log_time = add_time_offet(log_time, off_time)
            log_msg = match.group("message")

            if match.group("type") == "notice" and match.group("process") == "netifd":
                if (log_msg == "Interface 'wan' is now up"):
                    went_up = log_time
                elif (log_msg == "Interface 'wan' is now down"):
                    went_down = log_time
                    was_up_for = went_down - went_up
                    print "Link was up for %s until %s" % (was_up_for, datetime.strftime(went_down, "%c"))
        else:
            print "NO MATCH: %s" % line

if (went_down is None or went_up > went_down):
    was_up_for = duration_formatted((datetime.now() - went_up).total_seconds())
    print "Link has (apparently) been up for %s since %s (from system message log)" % (was_up_for, datetime.strftime(went_up, "%c"))
                                            
