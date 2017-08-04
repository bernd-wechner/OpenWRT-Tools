#!/bin/bash
#
# Consults the web service for a DDNS report from the perspective of the DDS diagnostics 
# web service (which is in this toolkit as index.php, default.css and ncdip)
#
# Returns JSON results if -j supplied
#
# TODO: pump standard results through elinks if I can get the package installed on the router 
# It's not in default repos, but it is available. I reported this here:
#	https://forum.turris.cz/t/elinks-on-the-omnia/4643/2 

# URL points to a remote service that provides the report
urlbase='https://thumbs-place.alwaysdata.net/ddns/'

# Set the URL argument
urlarg=""
if [[ $1 == "-j" ]]; then
	urlarg="json"
fi

result=$(curl -sG $urlbase --data-urlencode "$urlarg")
	
echo $result