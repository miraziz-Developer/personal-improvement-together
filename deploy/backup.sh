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

  offsite "$OUT/db-$day.dump"

  find "$OUT" -type f \( -name 'db-*.dump' -o -name 'storage-*.tar.gz' \) -mtime +"$KEEP_DAYS" -print -delete
  echo "[backup] $day: done"
}

# A copy that survives the server: the day's database dump, encrypted with BACKUP_PASSPHRASE,
# sent by the bot to BACKUP_CHAT_ID (Telegram keeps files up to 50 MB). Skipped when unset.
# Restore: openssl enc -d -aes-256-cbc -pbkdf2 -in db-<day>.dump.enc -out db.dump
offsite() {
  [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${BACKUP_CHAT_ID:-}" ] && [ -n "${BACKUP_PASSPHRASE:-}" ] || return 0
  command -v curl >/dev/null && command -v openssl >/dev/null || apk add --no-cache curl openssl >/dev/null
  openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE -in "$1" -out "$1.enc"
  if curl -sf -F chat_id="$BACKUP_CHAT_ID" -F document=@"$1.enc" \
    -F caption="PIT backup $(basename "$1") (encrypted)" \
    "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument" >/dev/null; then
    echo "[backup] sent off-site"
  else
    echo "[backup] off-site copy FAILED" >&2
  fi
  rm -f "$1.enc"
}

while true; do
  backup || echo "[backup] FAILED — will retry in an hour" >&2
  sleep 3600
done
