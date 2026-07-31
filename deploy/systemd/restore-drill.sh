#!/usr/bin/env bash
set -euo pipefail

# Restore into an explicitly separate staging database and directory.
# This script refuses to operate without an explicit confirmation.

: "$RESTIC_REPOSITORY"
: "$RESTIC_PASSWORD_FILE"
: "$RESTIC_SNAPSHOT"
: "$RESTORE_ROOT"
: "$RESTORE_DATABASE_URL"
: "$RESTORE_CONFIRM"

if [ "$RESTORE_CONFIRM" != "I_UNDERSTAND" ]; then
  echo "Refusing restore: set RESTORE_CONFIRM=I_UNDERSTAND explicitly." >&2
  exit 2
fi

mkdir -p "$RESTORE_ROOT"
restic --repo="$RESTIC_REPOSITORY" --password-file="$RESTIC_PASSWORD_FILE" restore "$RESTIC_SNAPSHOT" --target "$RESTORE_ROOT"

dump="$(find "$RESTORE_ROOT" -type f -name '*.dump' -print -quit)"
if [ -z "$dump" ]; then
  echo "No PostgreSQL custom dump found in restored snapshot." >&2
  exit 3
fi

pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" "$dump"
echo "Restore drill completed into the explicitly supplied staging targets."
