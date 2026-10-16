# Single-VPS production deployment

This runbook deploys the monorepo to one Ubuntu 24.04 VPS with Docker Compose,
Caddy automatic HTTPS, a Next.js standalone frontend, Django/Gunicorn, and
PostgreSQL. The existing `compose.yaml` remains development-only. Every command
below runs from the repository root.

## Public and private boundary

Caddy is the only service with host ports. It publishes TCP 80/443 and UDP 443.
PostgreSQL, Gunicorn, and Next.js use Docker-only `expose` entries and cannot be
reached through a host port.

Caddy sends these paths directly to Django:

- `/api/v1/payments/bale/webhook/` for provider callbacks;
- `/api/v1/health/` and `/api/v1/health/readiness/` for operations;
- `/admin` and `/admin/*` for the technical operator interface; and
- `/static/*` for Django Admin assets.

`/media/*` is served read-only from the shared media volume. Every other path,
including browser-facing `/api/*` routes, goes to Next.js so the same-origin BFF
continues to own browser cookies, CSRF/origin checks, refresh rotation, cart
credentials, and error mapping. Do not expose Django's container port or add a
generic `/api/*` proxy rule.

The `data` network is internal and contains only PostgreSQL and Django. The
`app` bridge contains Caddy, Next.js, and Django. Django needs outbound access
to Bale, while PostgreSQL has neither an external network nor a published port.
Caddy ignores client-provided forwarding headers by default and writes the
trusted `X-Forwarded-*` values consumed by Django. Do not put another proxy or
CDN in front without explicitly revisiting Caddy trusted-proxy configuration.

Next.js reaches Django through Caddy's Docker-only port 8080. That listener is
not published on the VPS; it normalizes `Host` and trusted HTTPS forwarding
headers so Django's production HTTPS redirect remains enabled without breaking
server-to-server BFF calls. Do not point `DJANGO_API_URL` directly at Gunicorn.

## VPS prerequisites

1. Install supported Docker Engine and the Docker Compose plugin on Ubuntu
   24.04. Do not install PostgreSQL, Node.js, Python, or Caddy on the host.
2. Point the selected domain's A record, and AAAA record only when IPv6 is fully
   configured, to the VPS.
3. Permit inbound SSH from the operator's trusted source and public TCP 80/443
   plus UDP 443. Do not permit 3000, 5432, or 8000.
4. Ensure the VPS clock is synchronized and that the Docker data directory has
   adequate monitored disk space.

Caddy obtains and renews the public certificate automatically after DNS is
correct and ports 80/443 are reachable.

## Production environment

Create the untracked environment file and restrict it before editing:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
editor .env.production
```

Replace every `REPLACE_WITH` value. `APP_DOMAIN` is a hostname only.
`APP_VERSION` is an immutable release identifier such as the approved source
revision. Generate distinct Django and JWT keys of at least 50 characters.
Generate a URL-safe random PostgreSQL password and use the identical value in
`POSTGRES_PASSWORD` and the password part of `DATABASE_URL`. Never commit this
file or paste its contents into logs or tickets.

Validate placeholders, secret length, file mode, and Compose interpolation:

```bash
sh deploy/check-production-env.sh .env.production
docker run --rm \
  -e APP_DOMAIN=example.com \
  -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.7-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

`example.com` in the validation command is reserved documentation data; replace
only the value in `.env.production` with the real domain.

## First deployment

Pull the pinned infrastructure images and build immutable application images:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  --profile tools pull caddy db backup maintenance
docker compose --env-file .env.production -f compose.production.yaml \
  build --pull backend frontend
```

Start PostgreSQL alone and wait for it to become healthy:

```bash
docker compose --env-file .env.production -f compose.production.yaml up -d db
docker compose --env-file .env.production -f compose.production.yaml ps
```

Validate Django and inspect the migration plan. Apply migrations exactly once
as an explicit release operation; no service startup runs migrations:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py check --deploy
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py migrate --plan
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py migrate --noinput
```

Start the application only after migration succeeds:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  up -d backend frontend caddy
docker compose --env-file .env.production -f compose.production.yaml ps
```

Create the initial superuser only when one does not already exist:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py createsuperuser
```

After the public HTTPS endpoint is healthy, register the exact derived Bale
webhook URL. Repeat this command only when the domain or webhook changes:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py set_bale_webhook
```

Complete the documented Bale sandbox flow before enabling real customer
payments.

## Health and logs

```bash
curl --fail --silent --show-error https://YOUR_DOMAIN/api/health
curl --fail --silent --show-error https://YOUR_DOMAIN/api/v1/health/
curl --fail --silent --show-error https://YOUR_DOMAIN/api/v1/health/readiness/
docker compose --env-file .env.production -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.production.yaml logs --tail=200 caddy frontend backend db
```

The first URL is Next.js-only liveness. Django liveness does not touch the
database. Readiness performs PostgreSQL `SELECT 1` and must gate traffic or
operator rollout decisions. Container logs rotate locally, but the VPS still
needs off-server log collection, retention, and alerts for health failures,
5xx spikes, restarts, disk pressure, PostgreSQL capacity, backup failures,
certificate renewal, and Bale webhook/recovery errors.

## Backup

The repository backup helper creates a PostgreSQL custom-format dump and a
media tarball in a new timestamped mode-700 directory. It never modifies the
database or media volume:

```bash
sh deploy/backup.sh /var/backups/naghsh-staging
```

Each backup includes `database.dump`, `media.tar.gz`, and `SHA256SUMS`. The
output is deliberately only a local staging copy. A production backup is not
complete until an operator-owned wrapper:

1. encrypts the archive with keys stored outside the VPS;
2. uploads it to the selected off-server storage provider;
3. verifies the remote size/checksum and retention policy;
4. emits a monitored success/failure signal; and
5. periodically restores a copy in an isolated environment.

Do not schedule the helper alone and mistake local files for backups. Keep local
staging retention bounded after the remote copy is verified. Also preserve the
production secrets through a separate secure escrow process; they are not put
inside the database/media archive.

PostgreSQL's custom format is compressed and is intended for `pg_restore`.
Media and database are captured close together but not as a filesystem-level
atomic snapshot; schedule during a quiet window or use provider snapshots when
a stricter recovery point is required.

## Restore

Test restoration on a separate VPS or separate Compose project first. A live
restore destroys the target database and replaces all media, so take and verify
a fresh safety backup before proceeding.

Stop public/application services while leaving PostgreSQL running:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  stop caddy frontend backend
cd /absolute/path/to/TIMESTAMPED_BACKUP
sha256sum -c SHA256SUMS
cd /path/to/repository
```

Replace `BACKUP_DIR` below with the absolute verified directory. Restore the
database:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  --profile tools run --rm --no-deps \
  -v BACKUP_DIR:/backup:ro maintenance sh -eu -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    dropdb --host=db --username="$POSTGRES_USER" --if-exists --force "$POSTGRES_DB"
    createdb --host=db --username="$POSTGRES_USER" --owner="$POSTGRES_USER" "$POSTGRES_DB"
    pg_restore --host=db --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --exit-on-error --no-owner --no-privileges /backup/database.dump
  '
```

Replace media only after confirming the backup path:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  --profile tools run --rm --no-deps \
  -v BACKUP_DIR:/backup:ro maintenance sh -eu -c '
    find /media -mindepth 1 -xdev -delete
    tar -C /media -xzf /backup/media.tar.gz
  '
```

Then run the current release's migrations explicitly, start the services, and
repeat all health and critical customer/Bale checks:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.production.yaml \
  up -d backend frontend caddy
```

## Updates and rollback

Before every update, create and upload a verified off-server backup. Place the
approved new source release on the VPS, change `APP_VERSION` to a new immutable
identifier, rerun environment/Caddy validation, then:

```bash
docker compose --env-file .env.production -f compose.production.yaml \
  build --pull backend frontend
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py migrate --plan
docker compose --env-file .env.production -f compose.production.yaml \
  run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.production.yaml \
  up -d backend frontend caddy
```

For a code-only rollback, restore the previous source release, set its previous
`APP_VERSION`, and run `up -d backend frontend caddy`. Do this only when applied
migrations are backward-compatible. If they are not, stop public/application
services and restore the pre-update database/media backup; do not improvise a
reverse migration. Keep old images until the release and restore window closes.

## Scheduled JWT cleanup

Run SimpleJWT cleanup once daily from exactly one host scheduler. For example,
create a root-owned systemd service whose `WorkingDirectory` is the repository:

```ini
[Unit]
Description=Naghsh-e Jahan expired JWT cleanup
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/repository
ExecStart=/usr/bin/docker compose --env-file .env.production -f compose.production.yaml run --rm --no-deps backend python manage.py flushexpiredtokens
```

Pair it with a daily persistent timer at an operator-selected low-traffic time:

```ini
[Unit]
Description=Run Naghsh-e Jahan expired JWT cleanup daily

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

Enable the timer and monitor failed units. Do not run the job independently in
every web container.

## Remaining launch requirements

- Real domain DNS and an email/contact process for certificate expiry alerts.
- Real, separately stored Django/JWT/database/Bale secrets.
- Successful Bale sandbox and fulfillment/cancellation/refund staging QA.
- Provider-specific encrypted off-server backup upload, retention, alerting,
  and a completed restore drill.
- Off-server logs/metrics and alert delivery.
- Measured VPS memory, CPU, disk, PostgreSQL connections, and a decision before
  raising `WEB_CONCURRENCY` above its conservative single-worker default.
