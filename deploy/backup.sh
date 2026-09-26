#!/bin/sh
# Daily backup of the database and proof photos, kept for $BACKUP_KEEP_DAYS days.
# Runs inside the `backup` service (postgres image, so pg_dump matches the server version).
# The file name carries the date, so restarts never produce a second backup for the same day.
set -eu

OUT=/backups
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

backup() {
  day=$(date +%Y-%m-%d)
  [ -f "$OUT/storage-$day.tar.gz" ] && return 0  # written last: its presence means the day is complete

  echo "[backup] $day: database"
  pg_dump -h postgres -U pit -d pit --format=custom --file="$OUT/db-$day.dump.part"
  mv "$OUT/db-$day.dump.part" "$OUT/db-$day.dump"

  echo "[backup] $day: photos"
  tar -czf "$OUT/storage-$day.tar.gz.part" -C /storage .
  mv "$OUT/storage-$day.tar.gz.part" "$OUT/storage-$day.tar.gz"

  find "$OUT" -type f \( -name 'db-*.dump' -o -name 'storage-*.tar.gz' \) -mtime +"$KEEP_DAYS" -print -delete
  echo "[backup] $day: done"
}

while true; do
  backup || echo "[backup] FAILED — will retry in an hour" >&2
  sleep 3600
done
