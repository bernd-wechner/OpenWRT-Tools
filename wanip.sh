#!/bin/bash
#
# Prints the apparent WAN address of this OpenWRT router

ip addr show pppoe-wan|grep inet|awk '{print $2}' | sed 's#/.*##'