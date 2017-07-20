#!/bin/bash
# Prints a list of domain names that are being managed by the DDNS service on this OpenWRT router
uci show ddns | grep .domain | sed -e "s/^.*=//" -e "s/^\([\"']\)\(.*\)\1\$/\2/g"