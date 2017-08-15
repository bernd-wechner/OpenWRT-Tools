#!/usr/bin/python
import re, json, subprocess, os, argparse, gzip
from datetime import datetime, timedelta

log_dir = '/var/log'
messages_file = 'messages'
messages_file_RE = messages_file + '\.(?P<num>[0-9]+)(\.gz)?' 

devnull = open(os.devnull, 'w')

parser = argparse.ArgumentParser(description='Report WAN up times as they appear in the system log file.',
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))

parser.add_argument('-l', '--Logs', action='store_true', help='Dump the actual log file entries found.')
parser.add_argument('-L', '--LogSummary', action='store_true', help='Print a summary of the message log file.')
parser.add_argument('-T', '--Test', nargs=1, help='Print a summary of the message log file.')

args = parser.parse_args()

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

# Then scan the messages log for down and up reports
went_up = None
went_down = None
count = 0

# Build the list of log files. The appear as messages, messages.1, messages.2 ... messages.10, messages.11 ...
log_files = [messages_file]

num_files = [f for f in os.listdir(log_dir) if re.match(messages_file_RE, f)]
dic_files = {}
for file in num_files:    
    num = re.match(messages_file_RE, file).group("num")
    dic_files[int(num)] = file
for num in sorted(dic_files.iterkeys()):
    log_files += [dic_files[num]]
log_files.reverse()

# Now parse the log files
output = []
for file in log_files:
    if file.endswith('.gz'):
        log_file = gzip.open(log_dir+'/'+file)
    else:
        log_file = open(log_dir+'/'+file) 
        
    file_line=0
    for line in log_file:
        file_line += 1
        match = re.match(log_pattern, line)
        if not match is None:
            count += 1
            off_pattern = r'([+-]\d\d:\d\d$)'
            off_time = re.search(off_pattern, match.group("time")).group(1)
            log_time = re.sub(off_pattern, '', match.group("time"))
            log_time = datetime.strptime(log_time, "%Y-%m-%dT%H:%M:%S")
            log_time = add_time_offet(log_time, off_time)
            log_msg = match.group("message")
            
            if count == 1:
                log_first = log_time

            if match.group("type") == "notice" and match.group("process") == "netifd":
                if args.Logs:
                    print line.strip()
                
                if (log_msg == "Interface 'wan' is now up"):
                    went_up = log_time
                elif (log_msg == "Interface 'wan' is now down"):
                    went_down = log_time
                    was_up_for = went_down - went_up
                    output += ["Link was up for %s until %s" % (was_up_for, datetime.strftime(went_down, "%c"))]
        elif len(line.strip()) > 0:
            print "Warning: Ill formed log line in %s (line %s) was ignored: %s" % (file, file_line, line)
        
log_last = log_time

# Report a summary of the system log file first if asked
if args.LogSummary:
    print "System log has %s entries, spanning %s between %s and %s" % (count, duration_formatted((log_last - log_first).total_seconds()), log_first, log_last)

# Then report the known up time
wan_status = get_wan_status()
if wan_status:
    up_time = datetime.now() - timedelta(seconds=wan_status["uptime"])
    print "Link has been up for %s since %s (from current WAN status)" % (duration_formatted(wan_status["uptime"]), datetime.strftime(up_time, "%c"))

# And finally the uptimes from the system log file
if len(output) > 0:
    print "\n".join(output)

if (went_down is None and not went_up is None  or went_up > went_down):
    was_up_for = duration_formatted((datetime.now() - went_up).total_seconds())
    print "Link has (apparently) been up for %s since %s (from system message log)" % (was_up_for, datetime.strftime(went_up, "%c"))
                                            