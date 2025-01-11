#!/bin/bash
# I keep a backup on /data/etc-backup. If something goes wrong, restore them from there.
rsync -r /etc/lighttpd/ssl/ /data/etc-backup/lighttpd/ssl

