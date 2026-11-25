#!/bin/sh
set -eu
mkdir -p /data
chown 1000:1000 /data
chmod u+rwx /data
if [ -L /data/.installation-id ]; then exit 1; fi
if [ -f /data/.installation-id ]; then chown 1000:1000 /data/.installation-id; chmod 600 /data/.installation-id; fi
exec setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs "$@"
