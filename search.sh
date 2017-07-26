#!/bin/bash
#
# Searches the router for a provided string (case sensitive)
#
# I often find myself wanting to understand a little better how OpenWRT or the Omnia work
# and am thus searching for certain settings and such without knowing where to find them. 
#
# Alas if I do a recursive grep from the filesystem root, it seems to take forever even hang, 
# and part of the reason I think is that grep does not discriminate file types and just searches 
# in every files it encounteres. But /sys and /proc are virtual file systems which we're not 
# interested in searching anyhow and binary files don't interest us. So we can speed things up 
# a little and avoid any hangs by more selectively searching.
#
# The command though is a little more than I want to remember! So here it is as a shell script.
#
# It relies in a partner script: textfile.sh
#
# It's still pretty slow and might restrict the filesize on the basis that pretty large majordomo 
# text databases are being scanned.   
#
#    Start at filesystem root
#       If path is /sys prune (don't descend)
#                            If path is /proc prune (don't descend)
#                                                 # Process only ordinary files
#                                                         Process only text files
#                                                                               Finally grep for the stuff
#                                                                                                 # But don't bug me with errors
find / -path /sys -prune -o -path /proc -prune -o -type f -exec textfile {} \; -exec grep -Hs $* {} \; 2>/dev/null
