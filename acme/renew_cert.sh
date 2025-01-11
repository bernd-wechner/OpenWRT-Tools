#!/bin/bash
#
# See:
#   https://doc.turris.cz/doc/en/public/letencrypt_turris_lighttpd
#   https://github.com/acmesh-official/acme.sh/wiki/How-to-issue-a-cert
#   https://github.com/acmesh-official/acme.sh/wiki/Options-and-Params
#
# They all seem so complcated comared with the simple example:
#
#   https://github.com/acmesh-official/acme.sh
shopt -s expand_aliases

# Configs
home=/root/.acme.sh
webroot=/www/acme
certhome=/etc/lighttpd/ssl
capath=/etc/ssl/certs

source $home/acme.sh.env

# Renew the cert
acme.sh --cron --home $home --webroot $webroot --certhome $certhome --ca-path $capath $@

# Restart lighttpd
/etc/init.d/lighttpd restart

# Copy cert to local loop server(s) and restart lighttpd there
$home/copy_cert.sh
