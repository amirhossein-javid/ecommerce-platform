#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: sh deploy/backup.sh /absolute/or/relative/backup-staging-directory" >&2
    exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${ENV_FILE:-"$ROOT_DIR/.env.production"}
COMPOSE_FILE="$ROOT_DIR/compose.production.yaml"

case "$1" in
    /*) BACKUP_ROOT=$1 ;;
    *) BACKUP_ROOT="$PWD/$1" ;;
esac

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

if [ ! -f "$ENV_FILE" ]; then
    echo "Production environment file not found: $ENV_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
final_dir="$BACKUP_ROOT/$timestamp"
working_dir="$final_dir.incomplete"

if [ -e "$final_dir" ] || [ -e "$working_dir" ]; then
    echo "Backup target already exists for timestamp $timestamp." >&2
    exit 1
fi

mkdir -m 700 "$working_dir"

compose exec -T db sh -eu -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null'

compose --profile tools run --rm --no-deps \
    --user "$(id -u):$(id -g)" \
    -v "$working_dir:/backup" \
    backup sh -eu -c '
        umask 077
        export PGPASSWORD="$POSTGRES_PASSWORD"
        pg_dump \
            --host=db \
            --username="$POSTGRES_USER" \
            --dbname="$POSTGRES_DB" \
            --format=custom \
            --no-owner \
            --no-privileges \
            --file=/backup/database.dump
        tar -C /media -czf /backup/media.tar.gz .
    '

(
    cd "$working_dir"
    sha256sum database.dump media.tar.gz > SHA256SUMS
)
chmod 600 "$working_dir/database.dump" "$working_dir/media.tar.gz" "$working_dir/SHA256SUMS"
mv "$working_dir" "$final_dir"

echo "Local staging backup created: $final_dir"
echo "This backup is not off-server or encrypted. Encrypt it, upload it to the configured off-server provider, verify the remote copy, and alert on any failure."
