#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${1:-"$ROOT_DIR/.env.production"}
COMPOSE_FILE="$ROOT_DIR/compose.production.yaml"

if [ ! -f "$ENV_FILE" ]; then
    echo "Production environment file not found: $ENV_FILE" >&2
    exit 1
fi

required_keys='APP_DOMAIN APP_VERSION POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL DJANGO_SECRET_KEY DJANGO_JWT_SIGNING_KEY PAYMENT_GATEWAY_CLASS BALE_BOT_TOKEN BALE_PROVIDER_TOKEN'

for key in $required_keys; do
    value=$(sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1)
    if [ -z "$value" ]; then
        echo "$key must be set in $ENV_FILE" >&2
        exit 1
    fi
    case "$value" in
        *REPLACE_WITH*)
            echo "$key still contains a placeholder in $ENV_FILE" >&2
            exit 1
            ;;
    esac
done

domain=$(sed -n 's/^APP_DOMAIN=//p' "$ENV_FILE" | tail -n 1)
if ! printf '%s\n' "$domain" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$' \
    || printf '%s\n' "$domain" | grep -q '\.\.'; then
    echo "APP_DOMAIN must be a hostname without a scheme, port, path, or spaces." >&2
    exit 1
fi

app_version=$(sed -n 's/^APP_VERSION=//p' "$ENV_FILE" | tail -n 1)
if ! printf '%s\n' "$app_version" | grep -Eq '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$'; then
    echo "APP_VERSION must be a valid immutable Docker tag." >&2
    exit 1
fi

postgres_db=$(sed -n 's/^POSTGRES_DB=//p' "$ENV_FILE" | tail -n 1)
postgres_user=$(sed -n 's/^POSTGRES_USER=//p' "$ENV_FILE" | tail -n 1)
postgres_password=$(sed -n 's/^POSTGRES_PASSWORD=//p' "$ENV_FILE" | tail -n 1)
database_url=$(sed -n 's/^DATABASE_URL=//p' "$ENV_FILE" | tail -n 1)
expected_database_url="postgresql://${postgres_user}:${postgres_password}@db:5432/${postgres_db}"
if [ "$database_url" != "$expected_database_url" ]; then
    echo "DATABASE_URL must match POSTGRES_DB, POSTGRES_USER, and the URL-safe POSTGRES_PASSWORD for host db:5432." >&2
    exit 1
fi

secret=$(sed -n 's/^DJANGO_SECRET_KEY=//p' "$ENV_FILE" | tail -n 1)
jwt_key=$(sed -n 's/^DJANGO_JWT_SIGNING_KEY=//p' "$ENV_FILE" | tail -n 1)
if [ "$secret" = "$jwt_key" ]; then
    echo "DJANGO_SECRET_KEY and DJANGO_JWT_SIGNING_KEY must differ." >&2
    exit 1
fi
if [ "${#secret}" -lt 50 ] || [ "${#jwt_key}" -lt 50 ]; then
    echo "Django and JWT secrets must each contain at least 50 characters." >&2
    exit 1
fi

mode=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || true)
case "$mode" in
    400|600) ;;
    *)
        echo "$ENV_FILE must have mode 600 (or read-only mode 400); current mode: ${mode:-unknown}." >&2
        exit 1
        ;;
esac

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet
echo "Production environment and Compose interpolation are valid."
