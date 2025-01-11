#!/usr/bin/python
#
# Scans all the system logs for wan up and down messages to report teh time between them
#
# A Work in progres, is being rewrritten currently

import re, json, subprocess, os, argparse, gzip
from datetime import datetime, timedelta

messages_file = 'messages'

messages_file_RE = messages_file + '[-.]?(?P<num>[0-9]+)?(\.gz)?'

# Check the USB mounted disk first for log files.
# if it can't be found try the standard /var/log.
# This assumes logging is configure by default to
# mounted USB drive on the router.
found_messages = False
log_dirs_to_check = ['/mnt/sda1/log', "/var/log"]
log_dirs = []

for log_dir in log_dirs_to_check:
    for file_name in os.listdir(log_dir):
        if re.match(messages_file_RE, file_name):
            found_messages = True
            log_dirs.append(log_dir)
            break

devnull = open(os.devnull, 'w')

parser = argparse.ArgumentParser(description='Report WAN up times as they appear in the system log file.',
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))

parser.add_argument('-l', '--Logs', action='store_true', help='Dump the actual log file entries found.')
parser.add_argument('-L', '--LogSummary', action='store_true', help='Print a summary of the message log file.')
parser.add_argument('-T', '--Test', action='store_true', help='Print a summary of the message log files.')
parser.add_argument('-w', '--Warnings', action='store_true', help='Show parser warnings (supressed by default)')

args = parser.parse_args()

# A sample message stream of the sort we want to summarise
# 2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' has link connectivity
# 2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' is setting up now
# 2017-05-29T00:09:43+10:00 notice netifd[]: Network device 'pppoe-wan' link is up
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is enabled
# 2017-05-29T00:09:43+10:00 notice netifd[]: Network alias 'pppoe-wan' link is up
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' has link connectivity
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is setting up now
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan' is now up
# 2017-05-29T00:09:43+10:00 notice firewall[]: Reloading firewall due to ifup of wan (pppoe-wan)
# 2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' has link connectivity
# 2017-05-29T00:09:32+10:00 notice netifd[]: Interface 'wan' is setting up now
# 2017-05-29T00:09:43+10:00 notice netifd[]: Network device 'pppoe-wan' link is up
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is enabled
# 2017-05-29T00:09:43+10:00 notice netifd[]: Network alias 'pppoe-wan' link is up
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' has link connectivity
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan6' is setting up now
# 2017-05-29T00:09:43+10:00 notice netifd[]: Interface 'wan' is now up
# 2017-05-29T00:09:43+10:00 notice firewall[]: Reloading firewall due to ifup of wan (pppoe-wan)
# 2017-05-29T00:09:54+10:00 notice netifd[]: Interface 'wan6' is now down
# 2017-05-29T00:09:54+10:00 notice netifd[]: Interface 'wan6' is disabled
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan6' has link connectivity loss
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is now down
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is disabled
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is enabled
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' is setting up now
# 2017-05-29T05:32:29+10:00 notice netifd[]: Interface 'wan' has link connectivity loss
# 2017-05-29T05:32:33+10:00 notice netifd[]: Interface 'wan' has link connectivity
# 2017-05-29T05:32:33+10:00 notice netifd[]: Interface 'wan' is setting up now
# 2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' is now down
# 2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' is disabled
# 2017-05-29T05:32:36+10:00 notice netifd[]: Interface 'wan' has link connectivity loss
# 2017-05-29T05:34:15+10:00 notice netifd[]: Interface 'wan' is enabled
# 2017-05-29T05:34:19+10:00 notice netifd[]: Interface 'wan' has link connectivity
# 2017-05-29T05:34:19+10:00 notice netifd[]: Interface 'wan' is setting up now


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


def duration_formatted(seconds, suffixes=['y', 'w', 'd', 'h', 'm', 's'], add_s=False, separator=' '):
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
                seconds = seconds % length  # Remove the part we are printing now

            time.append('%s%s' % (svalue, (suffix, (suffix, suffix + 's')[value > 1])[add_s]))

    return separator.join(time)


went_up = None
went_down = None


def read_messages():
    # Build the list of log files. They appear as messages, messages...
    # (where these can be messages.1 .2 etc or messages-date1 -date2 etc deppending on logrotate configurations)

    message_files = []
    for log_dir in log_dirs:
        message_files += [os.path.join(log_dir, f) for f in os.listdir(log_dir) if re.match(messages_file_RE, f)]

    log_files = sorted(message_files, key=lambda f: os.path.basename(f), reverse=True)
    # log_files.reverse()

    # Have observed two log file patterns. The time format seems to have altered at some point.
    log_pattern = r"(?P<time>\d\d\d\d-\d\d-\d\d \d\d:\d\d\:\d\d)\s+(?P<type>\w*)\s+(?P<process>[\w()./\-]*)\[(?P<pid>\d*)\]: (?P<message>.*)$"
    time_pattern = "%Y-%m-%d %H:%M:%S"
    up_pattern = r"Network device .*wan.* link is up"
    down_pattern = r"Network device .*wan.* link is down"

    # If testing just scan files and report how often these REs match
    if args.Test:
        # Print line_counts, recognised log format counts and  and match counts
        for file in log_files:
            if file.endswith('.gz'):
                log_file = gzip.open(file)
            else:
                log_file = open(file)

            lines = 0
            matched = 0
            recognised = 0
            ups = 0
            downs = 0
            for line in log_file:
                lines += 1

                match = re.match(log_pattern, line)

                if match:
                    recognised += 1
                    if match.group("type") == "notice" and match.group("process") == "netifd":
                        matched += 1

                        log_msg = match.group("message")
                        if re.match(up_pattern, log_msg):
                            ups += 1
                        elif re.match(down_pattern, log_msg):
                            downs += 1

            print file, lines, "lines, ", recognised, "recognised", matched, "matched", ups, "ups", downs, "downs"

    # Else build a time keyed dict on link up and down messages.
    else:
        updown = {}
        for file in log_files:
            if file.endswith('.gz'):
                log_file = gzip.open(file)
            else:
                log_file = open(file)

            for line in log_file:
                match = re.match(log_pattern, line)

                if not match is None:
                    # Extract the time
                    log_time = match.group("time")

                    # Parse it
                    log_time = datetime.strptime(log_time, time_pattern)

                    # And the log message
                    log_msg = match.group("message")

                    if match.group("type") == "notice" and match.group("process") == "netifd":
                        if re.match(up_pattern, log_msg):
                            updown[log_time] = "up"
                        elif re.match(down_pattern, log_msg):
                            updown[log_time] = "down"

        # Now walk the sorted keys and report
        for time in sorted(updown.keys()):
            print time, updown[time]

    exit()

    # Then scan the messages log for down and up reports
    count = 0

    # Build a time keyed dict of messages first
    output = []
    for file in log_files:
        if file.endswith('.gz'):
            log_file = gzip.open(log_dir + '/' + file)
        else:
            log_file = open(log_dir + '/' + file)

        file_line = 0
        link_up = False
        have_state = False
        for line in log_file:
            file_line += 1

            pattern = 0
            match = re.match(log_pattern1, line)
            if not match is None:
                pattern = 1
            else:
                match = re.match(log_pattern2, line)
                if not match is None:
                    pattern = 2

            if not match is None:
                count += 1

                # Timezone offset if present
                log_time = match.group("time")

                # Get the log time
                if pattern == 1:
                    log_time = datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S")
                elif pattern == 2:
                    off_pattern = r'([+-]\d\d:\d\d$)'
                    off_time = re.search(off_pattern, log_time).group(1)
                    log_time = re.sub(off_pattern, '', log_time)
                    log_time = datetime.strptime(log_time, "%Y-%m-%dT%H:%M:%S")
                    log_time = add_time_offet(log_time, off_time)

                # And the log message
                log_msg = match.group("message")

                if count == 1:
                    log_first = log_time

                if match.group("type") == "notice" and match.group("process") == "netifd":
                    if args.Logs:
                        print line.strip()

                    if (log_msg == "Interface 'wan' is now up"):
                        if not link_up:
                            link_up = True
                            went_up = log_time
                        elif have_state and args.Warnings:
                            print "Warning: Link went up when it was not down!"

                        have_state = True

                    elif (log_msg == "Interface 'wan' is now down"):
                        if link_up:
                            link_up = False
                            went_down = log_time
                            was_up_for = went_down - went_up
                            output += ["Link was up for %s until %s" % (was_up_for, datetime.strftime(went_down, "%c"))]
                        elif have_state and args.Warnings:
                            print "Warning: Link went down when it was not up!"

                        have_state = True

            elif len(line.strip()) > 0 and args.Warnings:
                print "Warning: Ill formed log line in \"%s\" (line %s) was ignored:\n\t%s" % (file, file_line, line)

    log_last = log_time

    # Report a summary of the system log file first if asked
    if args.LogSummary:
        print "System log has %s entries, spanning %s between %s and %s" % (count, duration_formatted((log_last - log_first).total_seconds()), log_first, log_last)

    return output


# Then report the known up time
wan_status = get_wan_status()
if wan_status:
    up_time = datetime.now() - timedelta(seconds=wan_status["uptime"])
    print "Link has been up for %s since %s (from current WAN status)" % (duration_formatted(wan_status["uptime"]), datetime.strftime(up_time, "%c"))

# Read the logged messages producing "output"
if found_messages:
    output = read_messages()

    # And finally the uptimes from the system log file
    if len(output) > 0:
        print "\n".join(output)

    if ((went_down is None and not went_up is None) or went_up > went_down):
        was_up_for = duration_formatted((datetime.now() - went_up).total_seconds())
        print "Link has (apparently) been up for %s since %s (from system message log)" % (was_up_for, datetime.strftime(went_up, "%c"))
