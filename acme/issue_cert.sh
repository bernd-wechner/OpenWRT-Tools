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
source /root/.acme.sh/acme.sh.env

home=/root/.acme.sh
webroot=/www/acme
certhome=/etc/lighttpd/ssl
capath=/etc/ssl/certs

echo "Reading domains from $certhome/domains"

# Read the domains
domains=()
while IFS= read -r line; do
   domains+=("--domain $line")
done < $certhome/domains

# echo "Aiming to renew these domains:"
# for domain in ${domains[@]}; do
#   echo -e "\t\"$domain\""
# done

# Issue the cert
acme.sh --issue ${domains[@]} --webroot $webroot --certhome $certhome --ca-path $capath --force

# Restart lighttpd
/etc/init.d/lighttpd restart

# Copy cert to local loop server(s) and restart lighttpd there
$home/copy_cert.sh
