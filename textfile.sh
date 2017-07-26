#!/bin/bash

# Expects a file as argument and sets return code to 0 (success) if it's a text file
# else to 1.
#
# USAGE:
#   text_file [FILE]
#
# EXAMPLE:
#   find . -type f -exec text_file {} \; grep
#
# Can accept more than one file on command line and returns 0 (success) if all are text files. 
# But I'm not sure that's of much use ;-)

binary_files=$(file --mime-encoding $* | awk -F '[[:space:]]*:[[:space:]]*' '($2 == "binary") {print $1}')

if [[ -z "$binary_files" ]]; then
	exit 0
else
	exit 1
fi