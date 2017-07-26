#!/usr/bin/python
#
# Prints /proc/net/arp, prepended with a column naming the device if possible,
# Uses MACnames -j and IPnames -j to build reference tables for names
#
# This was an effort to reproduce LuCI's Routes page with a CLI command.
# It's not quite the same though. /proc/net/arp has some entries LuCI doesn't display.
# And the whole point of the exercise was to display names in the list which LuCI does not (at present)

import argparse, os, sys, json, fileinput, subprocess, socket

def decodeFlags(hexstr):
	'''
	decodes a hex string (e.g. most typically "0x2") into an ARP flags descriptor using clues found here: 
		https://github.com/openwrt/linux/blob/master/include/uapi/linux/if_arp.h#L127
	'''
	hexint = int(hexstr, 16)
	bitmap = {0x2: "complete", 0x4: "permanent", 0x8: "publish", 0x10: "has trailers", 0x20: "use netmask", 0x40: "don't publish"}
	flags = []
	for bit in bitmap:
		if hexint & bit:
			flags += [bitmap[bit]]
			
	if len(flags) == 0:
		return "incomplete"
	else:
		return ", ".join(flags)

def decodeHWtype(hexstr):
	'''
	decodes a hex string (e.g. most typically "0x1") into a ARP HW descriptor using clues found here: 
		https://github.com/wireshark/wireshark/blob/master/epan/dissectors/packet-arp.c
	'''
	hexint = int(hexstr, 16)
	hwmap = ["NET/ROM", 
			 "Ethernet", 
			 "Experimental ethernet", 
			 "AX.25", 
			 "ProNET", 
			 "Chaos", 
			 "IEEE 802", 
			 "ARCNET", 
			 "Hyperchannel",
			 "Lanstar",
			 "Autonet",
			 "Localtalk",
			 "LocalNet",
			 "Ultra link",
			 "SMDS",
			 "Frame Relay",
			 "ATM",
			 "HDLC",
			 "Fibre Channel",
			 "ATM (RFC 2225)",
			 "Serial Line",
			 "ATM",
			 "MIL-STD-188-220",
			 "Metricom STRIP",
			 "IEEE 1394.1995",
			 "MAPOS",
			 "Twinaxial",
			 "EUI-64" ]
	return hwmap[hexint]

# Parse arguments

class OrderArgs(argparse.Action):
	'''
		A custom action for argparse that stores a pseudo argument "order" as a list of options in order.
		And the position in that order of a command line argument as its value. 
	'''
	def __call__(self, parser, namespace, values, option_string=None):
		order = getattr(namespace, 'order') if hasattr(namespace, 'order') else []
		if self.dest in order:
			sys.stderr.write("Warning: --%s should only be specified once. Subsequent instances are ignored.\n" % self.dest)
		else:
			order.append(self.dest)
			setattr(namespace, 'order', order)
			setattr(namespace, self.dest, len(order))

parser = argparse.ArgumentParser(description='Report "routes" in the same sense as the LuCI page of that name.\nThis is basically a presentation of the routers ARP cache.',
                                 epilog = "Augments the ARP cache with device names.\nThese are provided by MACnames and IPnames which must be installed as well.",
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))

parser.add_argument('-t', '--HWtype', action='store_true', help='Include the hardware type in the output.')
parser.add_argument('-d', '--Device', action='store_true', help='Include the ARP device in the output.LuCI calls this the "Interface"')
parser.add_argument('-f', '--Flags', action='store_true', help='Include the ARP flags in the output.')

parser.add_argument('-s', '--Summary', action='store_true', help='Include a summary in the output.')

parser.add_argument('-i', '--IPsort', action=OrderArgs, help='Sort results by IP address.', nargs=0)
parser.add_argument('-m', '--MACsort', action=OrderArgs, help='Sort results by HW address (MAC).', nargs=0)
parser.add_argument('-n', '--NameSort', action=OrderArgs, help='Sort results by Device name.', nargs=0)
parser.add_argument('-F', '--FlagSort', action=OrderArgs ,help='Sort results by ARP Flags.', nargs=0)

corj = parser.add_mutually_exclusive_group()
corj.add_argument('-c', '--csv', action='store_true', help='Print output in CSV format')
corj.add_argument('-j', '--json', action='store_true', help='Print output in JSON format')
parser.add_argument('-H', '--Header', action='store_true', help='Print header line')

args = parser.parse_args()

sortkeys = []
if hasattr(args, 'order'):
	for sorter in args.order:
		sortkeys += [sorter]
		
if args.FlagSort:
	args.Flags = True

ARP = "/proc/net/arp"

devnull = open(os.devnull, 'w')

MACnames = json.loads(subprocess.check_output(["MACnames", "-j"], stderr=devnull))
IPnames = json.loads(subprocess.check_output(["IPnames", "-j"], stderr=devnull))

result = {}

count_missing_MAC = 0
count_missing_name = 0
count_flags = {}

if not args.json:
	if args.csv:
		FMT = "%s, %s, %s"
		if args.HWtype:
			FMT += ", %s"
		if args.Device:
			FMT += ", %s"
		if args.Flags:
			FMT += ", %s"
	else:
		FMT = "%-25s %-17s %-22s"
		if args.HWtype:
			FMT += " %-12s"
		if args.Device:
			FMT += "  %-10s"
		if args.Flags:
			FMT += "  %-s"

for line in fileinput.input(ARP):
	if fileinput.isfirstline():
		if not args.json:
			vals = ["HW name", "IP address", "HW address (MAC)"]
			if args.HWtype:
				vals += ["HW type"]
			if args.Device:
				vals += ["Device"]
			if args.Flags:
				vals += ["Flags"]

			header = FMT % tuple(vals)
	else:
		fields = line.split()
		
		# The ARP Cache has these fields. LUCI only lists some IP, MAC and Device which it call sInterface
		IP = fields[0]
		HWtype = decodeHWtype(fields[1])
		Flags = decodeFlags(fields[2])
		MAC = fields[3].upper()
		Mask = fields[4]
		Device = fields[5]
		
		MACtest = MAC.strip(":0") 
		if len(MACtest) == 0:
			count_missing_MAC += 1

		if MAC in MACnames:
			name = MACnames[MAC]
		elif IP in IPnames:
			name = IPnames[IP]
		else:
			name = "<unknown>"
			count_missing_name += 1
		
		FlagList = Flags.split(", ")
		for Flag in FlagList:
			if Flag in count_flags:
				count_flags[Flag] += 1
			else:
				count_flags[Flag] = 1			
					
		keys = []
		for key in sortkeys:
			if key == "IPsort":
				keys += [socket.inet_aton(IP)]
			elif key == "MACsort":
				keys += [MAC]
			elif key == "NameSort":
				keys += [name]
			elif key == "FlagSort":
				keys += [Flags]
			
		keys += [fileinput.filelineno()]
		
		vals = [name, IP, MAC]
		if args.HWtype:
			vals += [HWtype]
		if args.Device:
			vals += [Device]
		if args.Flags:
			vals += [Flags]
		
		if args.json:
			result[tuple(keys)] = tuple(vals)
		else:
			result[tuple(keys)] = FMT % tuple(vals)

output = []	
if args.Header and not args.json:
	output += [header]

# Collect some summary info
count = len(result)

# Sort the results as requested
keys = sorted(result.iterkeys())

for key in keys:
	output += [result[key]]

if args.json:	
	print json.dumps(output)
else:
	for line in output:
		print line

if args.Summary and not args.json:
	print "%d total routes." % count
	if count_missing_name > 0: 
		print "%d with no identifiable name." % count_missing_name
	if count_missing_MAC > 0: 
		print "%d with no MAC." % count_missing_MAC
	for flag in count_flags:
		print "%d flagged %s." % (count_flags[flag], flag)
