#!/usr/bin/env bash
set -euo pipefail

# Run on a charity-controlled host with DATABASE_URL and RESTIC_REPOSITORY set.
# The script never deletes source data; restic retention is an explicit operator choice.

: "$DATABASE_URL"
: "$RESTIC_REPOSITORY"
: "$RESTIC_PASSWORD_FILE"

backup_root="${PROJECT_HOPE_BACKUP_ROOT:-}"
if [ -z "$backup_root" ]; then
  backup_root="/var/backups/project-hope"
fi
media_root="${PROJECT_HOPE_MEDIA_ROOT:-}"
if [ -z "$media_root" ]; then
  media_root="/var/lib/project-hope/media"
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_root"

pg_dump --format=custom --file="$backup_root/project-hope-$timestamp.dump" "$DATABASE_URL"
restic --repo="$RESTIC_REPOSITORY" --password-file="$RESTIC_PASSWORD_FILE" backup "$backup_root" "$media_root"
restic --repo="$RESTIC_REPOSITORY" --password-file="$RESTIC_PASSWORD_FILE" check

echo "Backup completed: $timestamp"
