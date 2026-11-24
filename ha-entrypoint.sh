#!/bin/sh
set -eu
# Never follow links or recursively chown the Supervisor's data directory.
# This image runs only as the HA app; ordinary Docker keeps its non-root entrypoint.
if [ "${OHPA_INSTALL_MODE:-}" != ha_app ]; then
  echo "HA image requires OHPA_INSTALL_MODE=ha_app" >&2
  exit 1
fi
if [ "${DATA_DIR:-/data}" != /data ]; then
  echo "HA app expects DATA_DIR=/data" >&2
  exit 1
fi
if [ ! -d /data ] || [ -L /data ]; then
  echo "OHPA: missing or invalid Supervisor /data mount" >&2
  exit 1
fi
chown 1000:1000 /data
chmod u+rwx /data
for file in /data/analytics.sqlite /data/analytics.sqlite-wal /data/analytics.sqlite-shm /data/analytics.sqlite-journal; do
  if [ -L "$file" ]; then
    echo "OHPA: refusing symlink at database path" >&2
    exit 1
  fi
  if [ -e "$file" ]; then
    [ -f "$file" ] || exit 1
    chown 1000:1000 "$file"
    chmod u+rw "$file"
  fi
done
echo "OHPA: persistent database directory prepared; starting as UID 1000"
if [ "$#" -eq 0 ]; then
  set -- uvicorn app:app --host 0.0.0.0 --port 8095 --no-access-log --no-proxy-headers
fi
exec setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs "$@"
