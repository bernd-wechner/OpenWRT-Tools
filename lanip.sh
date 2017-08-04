#!/bin/bash
#
# A general purpose tool for moving LAN IP configurations between configuration files, back files and screen.
#
# A LAN IP configuration is considered to be a list of Name, IP, MAC tuples that serve as a map between MAC, IP 
# and device names.
#
# Can report DHCP and Majordomo configurations or back them up, or restorer them from file.
#
# The DHCP configurations are used by both the DHCP server to allocate IP addresses to devices based on MAC
# and the DNS to resolve names to IP addressses. 
#
# The Majordomo configurations are used by Majordomo to render MAC addresses with a familiar name in reports.
# 
# Other configuration areas that map names, to IP or MAC can be added easily enough.
#
# At some level this was an exercise in aquiring bash skills and serves as a useful reference for any script that
# wants to handle command line arguments,work with lists or dictionaries (hashed arrays), match keys and more, lots
# of examples to draw from in here.

# A small function to trim whitespace from variables
# Config data may sometimes contain such errant whitepsace alas (seen in practice)
trim() { 
	# A Bash internals method
  	local var="$*"
  	var="${var#"${var%%[![:space:]]*}"}" # trim leading whitespace chars
  	var="${var%"${var##*[![:space:]]}"}" # trim trailing whitespace chars
	echo -n "$var"
	
	# A sed method
	#sed 's/^[[:blank:]]*//;s/[[:blank:]]*$//' <<< "$1"
	
	# An awk method 
	#awk '{$1=$1;print}' <<< $*
}

# A small routine to strip first and last quote from string for CSV reading
trim_quotes() {
	sed "s/^\([\"']\)\(.*\)\1\$/\2/g" <<< $1
}

OPTIONS=dDhcHs:t:nim
LONGOPTIONS=debug,DryRun,help,csv,Header,source:,target:,NameSort,IPsort,MACsort 

unknown_name=unknown
unknown_ip=unknown
unknown_mac=unknown

# temporarily store output to be able to check for errors
# activate advanced mode getopt quoting e.g. via “--options”
# pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")

if [[ $? -ne 0 ]]; then # getopt has complained about wrong arguments to stdout
    exit 1
fi

# use eval with "$PARSED" to properly handle the quoting
eval set -- "$PARSED"

# A list of sort keys, empty by default (used for sorting outputs)
SortKeys=()

# now process the options in order and nicely split until we see --
while true; do
    case "$1" in
        -h|--help)
            echo "usage: $0 [-h] [-c] [-H] [-s SOURCE] [-t TARGET] [SOURCE] [TARGET]"
            echo
            echo "Report, backup and load LAN IP configurations." 
            echo "Specifically concerned with name to IP to MAC mappings configured with uci on an OpenWRT router."
            echo
            echo "optional arguments:"
            echo "  -h, --help                  show this help message and exit"
            echo "  -c, --csv                   use CSV output on stdout, expect it on stdin"
            echo "  -H, --Header                add headers to output on stdout, expect one on stdin" 
            echo "  -s SOURCE, --source SOURCE  read data from SOURCE"
            echo "  -t TARGET, --target TARGET  send data to TARGET"
            echo "  -d, --debug					print a debug trace"
            echo "  -D, --DryRun				do not alter any configurations"
            echo
            echo "Can read from a list of sources, in which case they are merged if possible" 
            echo "Can write to a list of targets"
            echo
            echo "SOURCE and TARGET options:"
            echo "  multiple sources or targets can be specified (comma separated)"
            echo "  sources and targets can be sepcified with explicit -s and -t options or as the first and second argument."
            echo "  stdin - standard input"
            echo "  stdout - standard output"
            echo "  stderr - standard error"
            echo "  DHCP - the router's configured static DHCP leases (provides/expects Name, IP, MAC)"
            echo "  Majordomo - the router's configured Majordomo static names (provides/expects Name, MAC)"
            echo "  ALL - meaning all the uci sources/targets (same as "DHCP, Majordomo")"
            echo "  UCI - same as ALL"
            echo "  FILENAME - a legal filename in which case it is read or written as appropriate"
            exit
            ;;
        -d|--debug)
            debug=y
            shift
            ;;
        -D|--Dryrun)
            dryrun=y
            shift
            ;;
        -c|--csv)
            csv=y
            shift
            ;;
        -H|--Header)
            Header=y
            shift
            ;;
        -s|--source)
            source="$2"
            shift 2
            ;;
        -t|--target)
            target="$2"
            shift 2
            ;;
        -n|--NameSort)
        	if [[ $sort_by_name != y ]]; then 
        		SortKeys+=(lan_names); 
	        	sort_by_name=y
	        else
	        	echo "Warning: -n/--NameSort should only be specified once. Subsequent instances are ignored."
        	fi
            shift
            ;;
        -i|--IPsort)
            if [[ $sort_by_ip != y ]]; then 
            	SortKeys+=(lan_ips); 
	        	sort_by_ip=y
	        else
	        	echo "Warning: -i/--IPsort should only be specified once. Subsequent instances are ignored."
            fi
            shift
            ;;
        -m|--MACsort)
            if [[ $sort_by_mac != y ]]; then 
            	SortKeys+=(lan_macs); 
	        	sort_by_mac=y
	        else
	        	echo "Warning: -m/--MACsort should only be specified once. Subsequent instances are ignored."
            fi
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            exit 2
            ;;
    esac
done

if [[ $debug == y ]]; then
	echo "Sort keys: ${SortKeys[*]}" 	
fi

# Some helpers for parsing source and target values
UCI=("Majordomo" "DHCP" )

get_stvals() {
	if [[ $1 == "DHCP" || $1 == "Majordomo" || -f $1 ]]; then
		stvals=($1)
	elif [[ $1 == "ALL" || $1 == "UCI" ]]; then
		stvals=("${UCI[@]}")
	else
		IFS=', ' read -r -a stvals <<< $1
	fi
	echo "${stvals[@]}"
}

# Build the sources list
source_list=($(get_stvals $source) $(get_stvals $1))

if (( ${#source_list[@]} == 0 )); then source_list=("${UCI[@]}"); fi

declare -A source_hash
for source in ${source_list[@]}; do
	source_hash["$source"]=1
done

# Build the targets list
target_list=($(get_stvals $target) $(get_stvals $2))

if (( ${#target_list[@]} == 0 )); then target_list=(stdout); fi

declare -A target_hash
for target in ${target_list[@]}; do
	target_hash["$target"]=1
done

if [[ $debug == y ]]; then 	
	echo "sources: ${#source_hash[@]} (${!source_hash[@]})"
	echo "targets: ${#target_hash[@]} (${!target_hash[@]})"
fi

# Now we want to fetch data from the sources
# Data means: a list of (name, IP, MAC) tuples
# Bash can't do tuples, so three lists instead.

lan_names=()
lan_ips=()
lan_macs=()

#Given a a lan IP config (name, IP, MAC), stores it in the lists above andsets a result for feedback. 
store_lanip()
{
	result=""  # Return a result 
	
    local new_source=$(trim $1)
    local new_name=$(trim $2)
    local new_ip=$(trim $3)
    local new_mac=$(trim $4)
    
    # Skip an known (observed) bizarre situation where uci has a null entry for something
    if [[ $new_name == $unknown_name && $new_ip == $unknown_ip && $new_MAC == $unknown_MAC ]]; then result=Ignored; return; fi

	local i
	for i in "${!lan_names[@]}"; do
    	# Update with new data if available and check for conflicting data if present
        old_name=${lan_names[$i]}
        old_ip=${lan_ips[$i]}
        old_mac=${lan_macs[$i]}
        
	    # Check of identity between the new proposal and the existing entry
	    # If a name, IP or MAC is unknown in both cases it's not considered the 
	    # same. Lots of entries might have unknown values, this doesn't identify
	    # a match. 
        same_name=n
        if [[ $old_name == $new_name && $old_name != $unknown_name ]]; then same_name=y; fi

        same_ip=n
        if [[ $old_ip == $new_ip && $old_ip != $unknown_ip ]]; then same_ip=y; fi
        	
        same_mac=n
        if [[ $old_mac == $new_mac && $old_mac != $unknown_mac ]]; then same_mac=y; fi

       	# Check for name clash if there's an IP or MAC match
		if [[ $same_name == y && $same_ip == y && $same_mac == y ]]; then
			result=Unchanged
			breaktrail
		else
			# Now MAC is the best ID for a given device and arguably our key.
			if [[ $same_mac == y ]]; then
				# So if MAC is same, we should just check for 
				# new information (data replacing unknown) or 
				# conflicting information (new value for IP or name)
				if [[ $same_ip != y ]]; then
					if [[ $old_ip == $unknown_ip ]]; then 
						lan_ips[$i]=$new_ip
		       			result=Updated
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating IP for MAC:\n\tMAC: $old_mac\n\tIPs: $old_ip -> $new_ip"
	       				fi
					elif [[ $new_ip != $unknown_ip ]]; then 
	       				result="Conflicting IPs for MAC:\n\tMAC: $old_mac\n\tIPs: $old_ip -> $new_ip"
	       			else
		       			result=Ignored
	       			fi
				fi
			
				if [[ $same_name != y ]]; then
					if [[ $old_name == $unknown_name ]]; then 
						lan_names[$i]=$new_name
						# Update a max length track for new formatting
						if (( ${#new_name} > maxname )); then
							maxname=${#new_name}
						fi    	
		       			result=Updated
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating Name for MAC:\n\tMAC: $old_mac\n\tNames: $old_name -> $new_name"
	       				fi
					elif [[ $new_name != $unknown_name ]]; then 
		       			result="Conflicting Names for MAC:\n\tMAC: $old_mac\n\tNames: $old_name -> $new_name"
	       			else
		       			result=Ignored
	       			fi
				fi
			elif [[ $same_ip == y ]]; then
				# If MAC's differ, IP is the next strongest key and we want to repeat the checks
				if [[ $same_mac != y ]]; then
					if [[ $old_mac == $unknown_mac ]]; then 
						lan_macs[$i]=$new_mac
		       			result=Updated
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating MAC for IP:\n\tIP: $old_ip\n\tMACs: $old_mac -> $new_mac"
	       				fi
					elif [[ $new_mac != $unknown_mac ]]; then 
	       				result="Conflicting MACs for IP:\n\tIP: $old_ip\n\tMACs: $old_mac -> $new_mac"
	       			else
		       			result=Ignored
	       			fi
				fi

				if [[ $same_name != y ]]; then
					if [[ $old_name == $unknown_name ]]; then 
						lan_names[$i]=$new_name
		       			result=Updated
						# Update a max length track for new formatting
						if (( ${#new_name} > maxname )); then
							maxname=${#new_name}
						fi    	
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating Name for IP:\n\tIP: $old_ip\n\tNames: $old_name -> $new_name"
	       				fi
					elif [[ $new_names != $unknown_names ]]; then 
		       			result="Conflicting Names for IP:\n\tIP: $old_ip\n\tNames: $old_name -> $new_name"
	       			else
		       			result=Ignored
	       			fi
				fi
			elif [[ $same_name == y ]]; then
				# Finally, if MACs differ and IPs differ Name is the last possible (an weakest) key and we want to repeat the checks
				if [[ $same_mac != y ]]; then
					if [[ $old_mac == $unknown_mac ]]; then 
						lan_macs[$i]=$new_mac
		       			result=Updated
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating MAC for Name:\n\tName: $old_name\n\tMACs: $old_mac -> $new_mac"
	       				fi
					elif [[ $new_mac != $unknown_mac ]]; then 
	       				result="Conflicting MACs for Name:\n\tName: $old_name\n\tMACs: $old_mac -> $new_mac"
	       			else
		       			result=Ignored
	       			fi
				fi

				if [[ $same_ip != y ]]; then
					if [[ $old_ip == $unknown_ip ]]; then 
						lan_ips[$i]=$new_ip
		       			result=Updated
						if [[ $debug == y ]]; then 	
	       					echo -e "Merge: Updating IP for Name:\n\tName: $old_name\n\tIPs: $old_ip -> $new_ip"
	       				fi
					elif [[ $new_ip != $unknown_ip ]]; then 
	       				result="Conflicting IPs for Name:\n\tName: $old_name\n\tIPs: $old_ip -> $new_ip"
	       			else
		       			result=Ignored
	       			fi
				fi
			fi   	
		fi 
	done

	if [[ $result == "" ]]; then
    	# No matching entries were found to update, so safely add a new one
    	lan_names+=("$new_name")
    	lan_ips+=("$new_ip")
    	lan_macs+=("$new_mac")
		if [[ $debug == y ]]; then echo "Found new: \"$name\" \"$ip\" \"$mac\""; fi
    	result=Added
    	
		# Update a max length track for new formatting
		if (( ${#new_name} > maxname )); then
			maxname=${#new_name}
		fi    	
	fi	
}

# Given a uci target and item number in the lanip store will apply that lan IP configuration.
apply_lanip() {
    local target=$1
    local new_name=${lan_names[$2]}
    local new_ip=${lan_ips[$2]}
    local new_mac=${lan_macs[$2]}
    
	if [[ $target == DHCP ]]; then
		# Key on MAC if known else IP else name
		if [[ $new_mac != $unknown_mac || $new_ip != $unknown_ip ]]; then
			local mac_index=-1
			local ip_index=-1
			local name_index=-1
			i=0
			while uci get dhcp.@host[$i] >& /dev/null; do
				old_name=$(uci get dhcp.@host[$i].name 2>/dev/null)
				old_ip=$(uci get dhcp.@host[$i].ip 2>/dev/null)
				old_mac=$(uci get dhcp.@host[$i].mac 2>/dev/null | tr [a-z] [A-Z])
				if [[ $new_mac == $old_mac && $old_mac != $unknown_mac ]]; then
					mac_index=$i 
					break
				elif [[ $new_ip == $old_ip && $old_ip != $unknown_ip ]]; then	
					ip_index=$i
					# don't break, keep looking for a MAC match which has priority over an IP match
				elif [[ $new_name == $old_name && $old_name != $unknown_name ]]; then	
					name_index=$i
					# don't break, keep looking for a MAC match which has priority over an IP match
				fi
				((i++))
			done
			
			if (( $mac_index >= 0 || $ip_index >= 0 || $name_index >= 0 )); then
				if   (( $mac_index >= 0 )); then index=$mac_index
				elif (( $ip_index >= 0 ));  then index=$ip_index
				else index=$name_index; fi

				# Fetch the old data, these data may reflect the last host, not the matched one
				old_name=$(uci get dhcp.@host[$index].name 2>/dev/null)
				old_ip=$(uci get dhcp.@host[$index].ip 2>/dev/null)
				old_mac=$(uci get dhcp.@host[$index].mac 2>/dev/null | tr [a-z] [A-Z])
				if [[ $old_name == "" ]]; then old_name=$unknown_name; fi
				if [[ $old_ip == "" ]]; then old_ip=$unknown_ip; fi
				if [[ $old_mac == "" ]]; then old_mac=$unknown_mac; fi

				# Check for a change
				if [[ $new_name != $old_name || $new_ip != $old_ip || $new_mac != $old_mac ]]; then
					if [[ $debug == y ]]; then 
						echo -e "Setting DHCP config: $index $old_mac->$new_mac $old_ip->$new_ip $old_name->$new_name";					 
					fi
				
					if [[ $dryrun != y ]]; then	
						if [[ $new_name == $unknown_name ]]; then
							uci delete dhcp.@host[$index].name
						else
							uci set dhcp.@host[$index].name="$new_name"
						fi
					
						if [[ $new_ip == $unknown_ip ]]; then
							uci delete dhcp.@host[$index].ip
						else
							uci set dhcp.@host[$index].ip="$new_ip"
						fi
					
						if [[ $new_mac == $unknown_mac ]]; then
							uci delete dhcp.@host[$index].mac
						else
							uci set dhcp.@host[$index].mac="$new_mac"
						fi
					fi
				fi
			else
				if [[ $debug == y ]]; then echo -e "Setting DHCP config: new $new_mac $new_ip $new_name"; fi	
				if [[ $dryrun != y ]]; then	
					uci add dhcp host
					if [[ $new_name != $unknown_name ]]; then
						uci set dhcp.@host[-1].name="$new_name"
					fi
				
					if [[ $new_ip != $unknown_ip ]]; then
						uci set dhcp.@host[-1].ip="$new_ip"
					fi
				
					if [[ $new_mac != $unknown_mac ]]; then
						uci set dhcp.@host[-1].mac="$new_mac"
					fi
				fi
			fi
			if [[ $dryrun != y ]]; then uci commit dhcp; fi
		fi
	elif [[ $target == Majordomo ]]; then
		if [[ $new_mac != $unknown_mac ]]; then
			local mac_index=-1
			local name_index=-1
			i=0
			while uci get majordomo.@static_name[$i] >& /dev/null; do
				old_name=$(uci get majordomo.@static_name[$i].name 2>/dev/null)
				old_mac=$(uci get majordomo.@static_name[$i].mac 2>/dev/null | tr [a-z] [A-Z])
				if [[ $new_mac == $old_mac && $old_mac != $unknown_mac ]]; then
					mac_index=$i 
					break; 
				elif [[ $new_name == $old_name && $old_name != $unknown_name ]]; then
					name_index=$i 
				fi
				((i++))
			done
			
			if (( $mac_index >= 0 || $name_index >= 0 )); then
				if (( $mac_index >= 0 )); then index=$mac_index
				else index=$name_index; fi

				# Fetch the old data, these data may reflect the last host, not the matched one
				old_name=$(uci get majordomo.@static_name[$index].name 2>/dev/null)
				old_mac=$(uci get majordomo.@static_name[$index].mac 2>/dev/null | tr [a-z] [A-Z])
				if [[ $old_name == "" ]]; then old_name=$unknown_name; fi
				if [[ $old_mac == "" ]]; then old_mac=$unknown_mac; fi
					
				# Check for a change
				if [[ $new_name != $old_name || $new_mac != $old_mac ]]; then
					if [[ $debug == y ]]; then 
						echo -e "Setting Majordomo config: $index $old_mac->$new_mac $old_name->$new_name"; 
					fi
						
					if [[ $dryrun != y ]]; then	
						if [[ $new_name == $unknown_name ]]; then
							uci delete majordomo.@static_name[$index].name
						else
							uci set majordomo.@static_name[$index].name="$new_name"
						fi
					
						if [[ $new_mac == $unknown_mac ]]; then
							uci delete majordomo.@static_name[$index].mac
						else
							uci set majordomo.@static_name[$index].mac="$new_mac"
						fi
					fi
				fi
			else
				if [[ $debug == y ]]; then echo -e "Setting Majordomo config: new $new_mac $new_name"; fi	
				if [[ $dryrun != y ]]; then	
					uci add majordomo static_name
					uci set majordomo.@static_name[-1].name="$new_name"
					uci set majordomo.@static_name[-1].mac="$new_mac"
				fi
			fi
			if [[ $dryrun != y ]]; then uci commit majordomo; fi
		fi 
	fi
}

# quicksorts positional arguments
# return is in array qsort_ret
# First argument is a function name that takes two arguments and compares them
# Thanks to gniourf_gniourf on Stackoverflow
# https://stackoverflow.com/questions/7442417/how-to-sort-an-array-in-bash
qsort() {
   (($#<=1)) && return 0
   local compare_fun=$1
   shift
   local stack=( 0 $(($#-1)) ) beg end i pivot smaller larger
   qsort_ret=("$@")
   while ((${#stack[@]})); do
      beg=${stack[0]}
      end=${stack[1]}
      stack=( "${stack[@]:2}" )
      smaller=() larger=()
      pivot=${qsort_ret[beg]}
      for ((i=beg+1;i<=end;++i)); do
         if "$compare_fun" "${qsort_ret[i]}" "$pivot"; then
            smaller+=( "${qsort_ret[i]}" )
         else
            larger+=( "${qsort_ret[i]}" )
         fi
      done
      qsort_ret=( "${qsort_ret[@]:0:beg}" "${smaller[@]}" "$pivot" "${larger[@]}" "${qsort_ret[@]:end+1}" )
      if ((${#smaller[@]}>=2)); then stack+=( "$beg" "$((beg+${#smaller[@]}-1))" ); fi
      if ((${#larger[@]}>=2)); then stack+=( "$((end-${#larger[@]}+1))" "$end" ); fi
   done
}

# A simple function to convert an IP address to a sortable decimal.
ip2dec () {
    local a b c d ip=$@
    IFS=. read -r a b c d <<< "$ip"
    printf '%d\n' "$((a * 256 ** 3 + b * 256 ** 2 + c * 256 + d))"
}

# A simple comparison function for qsort, which takes up to three keys
compare() {
	key1=${SortKeys[0]}
	key2=${SortKeys[1]}
	key3=${SortKeys[2]}

	key_1="$(eval echo \${${key1}[$1]})"
	key_2="$(eval echo \${${key1}[$2]})"
	if [[ "$key1" == "lan_ips" ]]; then
		key_1=$(ip2dec $key_1)
		key_2=$(ip2dec $key_2)
	fi
	
	if [[ $key2 != ""  && "$key_1" == "$key_2" ]]; then
		key_1="$(eval echo \${${key2}[$1]})"
		key_2="$(eval echo \${${key2}[$2]})"
		if [[ "$key2" == "lan_ips" ]]; then
			key_1=$(ip2dec $key_1)
			key_2=$(ip2dec $key_2)
		fi
	
		if [[ $key3 != "" && "$key_1" == "$key_2" ]]; then
			key_1="$(eval echo \${${key3}[$1]})"
			key_2="$(eval echo \${${key3}[$2]})"
			if [[ "$key3" == "lan_ips" ]]; then
				key_1=$(ip2dec $key_1)
				key_2=$(ip2dec $key_2)
			fi
		
			[[ "$key_1" < "$key_2" ]] && return 0 || return 1
		else
			[[ "$key_1" < "$key_2" ]] && return 0 || return 1
		fi 
	else
		[[ "$key_1" < "$key_2" ]] && return 0 || return 1
	fi 
}

# bash reads stdin from filehandle 0 and writes stdout to filehandle 1, stderr to file handle 2
# exec points file handles for rest of script. Point fha to fhb with fha>&fhb
# We save the three std filehandles so we can route them per request belo
exec 3>&0 # File handle 3 now remembers stdin 
exec 4>&1 # File handle 4 now remembers stdout
exec 5>&2 # File handle 5 now remembers stderr

maxname=0
sources_ok=y
for source in "${!source_hash[@]}"; do		
	if [[ $debug == y ]]; then echo -e "\nSourcing: $source"; fi	
	if [[ $source == DHCP ]]; then
		i=0
		while uci get dhcp.@host[$i] >& /dev/null; do
			name=$(uci get dhcp.@host[$i].name 2>/dev/null)
			ip=$(uci get dhcp.@host[$i].ip 2>/dev/null)
			mac=$(uci get dhcp.@host[$i].mac 2>/dev/null | tr [a-z] [A-Z])
			
			if [[ $name == "" ]]; then name=$unknown_name; fi
			if [[ $ip == "" ]]; then ip=$unknown_ip; fi
			if [[ $mac == "" ]]; then mac=$unknown_mac; fi

			store_lanip "$source" "$name" "$ip" "$mac"
			
			if [[ ! $result =~ (Added|Updated|Ignored) ]]; then 
				echo -e $result >&2;
				sources_ok=n 
			fi 
			((i++))
		done
	elif [[ $source == Majordomo ]]; then
		i=0
		while uci get majordomo.@static_name[$i] >& /dev/null; do
			name=$(uci get majordomo.@static_name[$i].name 2>/dev/null)
			ip=$unknown_ip
			mac=$(uci get majordomo.@static_name[$i].mac 2>/dev/null | tr [a-z] [A-Z])
			
			if [[ $name == "" ]]; then name=$unknown_name; fi
			if [[ $ip == "" ]]; then ip=$unknown_ip; fi
			if [[ $mac == "" ]]; then mac=$unknown_mac; fi

			store_lanip "$source" "$name" "$ip" "$mac"

			if [[ ! $result =~ (Added|Updated|Ignored) ]]; then 
				echo -e $result >&2; 
				sources_ok=n 
			fi 
			((i++))
		done
	else
		# Draw the input from stdin or a disk file as requested
		if [[ $source == "" || $source == "stdin" || $source == "0" || $source == "-" ]]; then
			exec 0<&3 
		else
			exec 0<$source
		fi
	
		i=0
		while IFS= read -r line || [[ -n "$line" ]]; do
			if (( $i > 0 )) || [[ $Header != y ]]; then 
				if [[ $csv == y ]]; then
					ifs=','
				else
					ifs=' '
				fi
				IFS=$ifs read -r -a parts <<< "$line"
				name=$(trim $(trim_quotes ${parts[0]}))
				ip=$(trim $(trim_quotes ${parts[1]}))
				mac=$(trim $(trim_quotes ${parts[2]}))
				
				if [[ $name == "" ]]; then name=$unknown_name; fi
				if [[ $ip == "" ]]; then ip=$unknown_ip; fi
				if [[ $mac == "" ]]; then mac=$unknown_mac; fi
	
				store_lanip "$source" "$name" "$ip" "$mac"
				
				if [[ ! $result =~ (Added|Updated|Ignored) ]]; then 
					echo -e $result >&2; 
					sources_ok=n 
				fi
			elif [[ $debug == y ]]; then
				echo "Skipping header in $source" >&2; 
			fi 
			((i++))
		done
	fi
done

# And finally we want to send data from the targets

maxip=15	# = 4x3 + 3
maxmac=17	# = 6x2 + 5

fmt="%-${maxname}s %-${maxip}s %-${maxmac}s"
if [[ $csv == y ]]; then fmt="\"%s\", \"%s\", \"%s\""; fi
if [[ $Header == y ]]; then	header=$(printf "$fmt\n" "Device Name" "IP" "MAC"); fi
	
# Sort the results if requested
order=(${!lan_names[@]})
if (( ${#SortKeys[@]} > 0 )); then
	qsort compare "${!lan_names[@]}"
	order=(${qsort_ret[@]})			
fi	
	
for target in "${!target_hash[@]}"; do
	if [[ $debug == y ]]; then echo -e "\nTargeting: $target"; fi	
	if [[ $target =~ (DHCP|Majordomo) ]]; then
		if [[ $sources_ok == y ]]; then
			for i in "${order[@]}"; do
				name=${lan_names[$i]}
				ip=${lan_ips[$i]}
				mac=${lan_macs[$i]}
				
				apply_lanip "$target" "$i"
			done
		else
			echo "$target configs NOT written. Sources not consistent." >&2;
		fi 
	else
		# Point the output to stdout, stderr or a disk file as requested
		if [[ $target == "" || $target == "stdout" || $target == "1" || $target == "-" ]]; then
			exec 1>&4 2>&5
		elif [[ $target == "stderr" || $target == "2" ]]; then
			exec 1>&4 2>&5
		else
			exec 1>$target 2>&5
		fi
	
		if [[ $Header == y ]]; then echo "$header"; fi
		
		for i in "${order[@]}"; do
			line=$(printf "$fmt\n" "${lan_names[$i]}" "${lan_ips[$i]}" "${lan_macs[$i]}")
			echo "$line"
		done
	fi	
done