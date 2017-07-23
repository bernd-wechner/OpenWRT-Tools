#!/bin/bash
#
# Tries to identify who owns a given IP address

whois $1 | grep "descr:" | sed -E "s/^.*?\:\s*//"