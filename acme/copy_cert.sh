#!/bin/bash
rsync -rL "/etc/lighttpd/ssl" "root@nephele.lan:/etc/lighttpd"
ssh root@nephele.lan "service lighttpd restart"
