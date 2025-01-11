#!/bin/bash
# I keep a backup on /data/etc-backup. If something goes wrong, restore them from there.
rsync -r /data/etc-backup/lighttpd/ssl/ /etc/lighttpd/ssl
# Restart lighttpd
/etc/init.d/lighttpd restart

