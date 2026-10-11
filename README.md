# Naghsh-e Jahan ecommerce monorepo

Production-oriented ecommerce application with a Django/DRF API, PostgreSQL,
and a Next.js App Router storefront/BFF, orchestrated locally with Docker. The
customer-facing application is a Persian RTL store for Isfahan handicrafts under
the Naghsh-e Jahan identity.

The repository is organized as a monorepo. The Django application and its
Python tooling live in `backend/`, and the Next.js application lives in
`frontend/`; repository-level Compose, environment, and documentation files
remain at the root.

The executable Next.js integration boundary is documented in
[`FRONTEND_HANDOFF.md`](FRONTEND_HANDOFF.md).

## Current scope

The Django API implements email-based customer authentication, profiles and
owned addresses, the public category/product catalog, guest and customer carts,
explicit cart merge, transactional checkout and inventory reservations, owned
order history/detail and cancellation, fulfillment lifecycle, payments, Bale
verification/webhooks, refund tracking, and operator administration. Django is
authoritative for identity, ownership, prices, stock, totals, lifecycle state,
payment truth, and review moderation.

The Next.js storefront implements the Persian RTL homepage, catalog discovery,
search/filter/sort/pagination, product detail and add-to-cart, guest and customer
carts, authentication, account/profile/address management, checkout, payment
handoff and authoritative result handling, and paginated customer order
history/detail. Product detail also includes approved customer reviews, rating
aggregates, official store replies, authenticated submission, moderation-status
display, and deletion. Authorized operators can use the focused Next.js
operations dashboard at `/dashboard` for backend-derived order metrics, order
fulfillment, review moderation, and one official reply per review. Order and
review permissions stay independent, and the legacy `/management/reviews` URL
redirects to `/dashboard/reviews`.

Django Admin remains the separate technical/operator back office at `/admin/`.
It uses a dependency-free Persian RTL Naghsh-e Jahan theme built on Django's
native templates and CSS variables; existing model permissions, validation,
read-only protections, and domain-backed actions remain authoritative.
Storefront product cards display the current approved-review average and count,
or the explicit Persian unrated state when no approved reviews exist.
Its thin same-origin BFF stores JWTs and the guest-cart token in
HttpOnly cookies, enforces origin checks on mutations, serializes refresh-token
rotation, and keeps personalized responses private/no-store. Detailed endpoint
sequences and ownership/error behavior belong in `FRONTEND_HANDOFF.md` rather
than being duplicated here.

Product-review endpoint shapes, the no-edit lifecycle, moderation rules, and
frontend integration details are recorded in `FRONTEND_HANDOFF.md`.

## Local setup with Docker

1. Copy `.env.example` to `.env` and replace the development secret.
2. Start the services:

   ```bash
   docker compose up --build
   ```

Docker Compose runs the complete local stack without requiring Python, Node.js,
or npm on the host:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Uploaded media: `http://localhost:8000/media/` (development only)

Useful backend endpoints:

- Health check: `GET /api/v1/health/`
- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

Development Compose intentionally applies migrations before starting Django's
development server. This behavior is confined to `compose.yaml`; the production
image never runs migrations as part of web startup.

The frontend source is bind-mounted for development reloads. Its Linux
`node_modules` and `.next` cache live in Docker named volumes so they are not
mixed with host artifacts. Inside Compose, the server-only `DJANGO_API_URL`
defaults to `http://web:8000`, where `web` is the Django service name. Compose
uses Next.js development with Webpack and a one-second file-watch poll so edits
are detected reliably through Docker Desktop bind mounts. Production builds and
direct host development keep the Next.js defaults.

Without an explicit environment override, Compose uses
`apps.payments.gateways.UnavailablePaymentGateway`; it does not include a fake
payment simulator. A copied `.env.example` selects Bale, but real testing still
requires the external Bale credentials, public HTTPS webhook, and Mini App flow
documented below. The frontend must not simulate a successful payment when that
provider setup is absent.

## Quality checks

Run these inside the web container:

```bash
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web python manage.py check
```

Run frontend checks in its container:

```bash
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run typecheck
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run build
```

## Production settings and security

Production uses `config.settings.production`, always disables `DEBUG`, redirects
HTTP to HTTPS, uses secure/HttpOnly cookies, denies framing, and enables a
one-hour HSTS policy by default. Production startup fails when required settings
are missing or retain known development/placeholder values.

Required production configuration:

- `DJANGO_SETTINGS_MODULE=config.settings.production`: set this explicitly for
  web replicas, release commands, and scheduled jobs, even though the image has
  the same default.
- `DJANGO_SECRET_KEY`: a random value of at least 50 characters. It must not be
  a Django-generated or documented placeholder.
- `DJANGO_JWT_SIGNING_KEY`: a separate random value of at least 50 characters.
- `DJANGO_ALLOWED_HOSTS`: explicit comma-separated hostnames. `*`, URL schemes,
  and paths are rejected.
- `DATABASE_URL`: the production PostgreSQL URL. The Compose development URL is
  rejected.

Optional production configuration:

- `DJANGO_SECRET_KEY_FALLBACKS`: comma-separated previous strong keys used only
  during a controlled Django secret rotation. Remove old keys after the
  rotation window.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated HTTPS origins that need to make
  trusted cross-origin unsafe requests. Do not add an origin merely because it
  is present in the CORS allowlist.
- `DJANGO_CORS_ALLOWED_ORIGINS`: comma-separated HTTPS browser frontend origins.
  CORS is limited to `/api/`, never allows every origin, and does not allow
  cookie credentials. Bearer authorization and `X-Cart-Token` are supported.
- `DJANGO_LOG_LEVEL` and `DJANGO_APP_LOG_LEVEL`: `INFO`, `WARNING`, `ERROR`, or
  `CRITICAL`; both default to `INFO`. Logs go to the process console for the
  deployment environment to collect.

`DJANGO_SECURE_HSTS_SECONDS` defaults to `3600`. Increase it gradually only
after HTTPS works reliably for every production request. Enable
`DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` only when every subdomain is permanently
HTTPS-capable. `DJANGO_SECURE_HSTS_PRELOAD=True` is rejected unless subdomains
are included and HSTS is at least one year; browser preload-list submission is
a separate, deployment-specific decision.

Set `DJANGO_TRUST_X_FORWARDED_PROTO=True` only when Django runs behind a trusted
reverse proxy that strips any client-supplied `X-Forwarded-Proto` header and
sets it from the actual connection. Leave it disabled when that assumption does
not hold. No proxy vendor or network topology is assumed by the application.

### TLS and reverse-proxy boundary

The production image runs Gunicorn over plain HTTP inside the container; it does
not terminate public TLS. The deployment ingress or reverse proxy must provide
the public HTTPS endpoint and must not expose Gunicorn directly to untrusted
public traffic. Because Django enforces `SECURE_SSL_REDIRECT`, a proxy that
terminates TLS and forwards HTTP to the container must provide a trustworthy
secure-scheme signal. For the supported header-based path, it must discard any
client-supplied `X-Forwarded-Proto`, set that header itself, and the application
must set `DJANGO_TRUST_X_FORWARDED_PROTO=True`. Enabling that setting without
this sanitizing trust boundary permits clients to forge whether a request was
secure; omitting it behind an HTTP upstream causes redirect loops for normal
HTTPS requests.

`DJANGO_ALLOWED_HOSTS` contains request hostnames, without schemes or paths.
`DJANGO_CORS_ALLOWED_ORIGINS` contains HTTPS browser origins allowed to read the
API, while `DJANGO_CSRF_TRUSTED_ORIGINS` is only for origins trusted to submit
CSRF-protected unsafe requests. These lists are separate and must be populated
from the actual public domains; a frontend origin does not automatically belong
in the CSRF list.

### Application request throttling

Abuse-sensitive authentication, cart mutation, checkout, payment, review
mutation, and Bale webhook endpoints use DRF scoped throttles. Anonymous scopes
are keyed by client IP and authenticated commerce scopes by user ID. The limits
are configured with:

- `DJANGO_THROTTLE_AUTH_REGISTER_RATE`
- `DJANGO_THROTTLE_AUTH_LOGIN_RATE`
- `DJANGO_THROTTLE_AUTH_REFRESH_RATE`
- `DJANGO_THROTTLE_CART_MUTATION_RATE`
- `DJANGO_THROTTLE_CHECKOUT_RATE`
- `DJANGO_THROTTLE_PAYMENT_INITIATE_RATE`
- `DJANGO_THROTTLE_PAYMENT_VERIFY_RATE`
- `DJANGO_THROTTLE_BALE_WEBHOOK_RATE`
- `DJANGO_THROTTLE_REVIEW_MUTATION_RATE`

Rates use DRF's positive `<requests>/<period>` format, such as `10/minute`.
By default `DJANGO_THROTTLE_NUM_PROXIES=0`, so client-supplied
`X-Forwarded-For` is ignored and `REMOTE_ADDR` is used. Set it to the exact
number of trusted ingress proxies only when every proxy in that chain strips or
replaces client-supplied forwarding headers. An incorrect value can allow IP
throttle bypasses or combine unrelated clients under one identity.

The default local-memory cache keeps this protection dependency-free and is
appropriate for the image's conservative single-worker default. Each worker or
replica has an independent counter; deployments that scale beyond one process
must add a trusted shared Django cache or enforce equivalent limits at the
ingress. DRF throttling is defense in depth, not a substitute for provider or
network-level denial-of-service protection.

## Production image and deployment lifecycle

The default backend Docker build installs production requirements, collects immutable
static assets, and creates a non-root image. It does not contact PostgreSQL or
embed deployment credentials while building:

```bash
docker build -t ecommerce-api ./backend
```

Provide the required production settings described above through the deployment
environment or secret manager. The image defaults to
`DJANGO_SETTINGS_MODULE=config.settings.production`; keep that value explicit in
the production environment so one-off management commands and web replicas use
the same settings. Development Compose overrides it with the development
settings. Then use this provider-neutral release sequence:

1. Run migrations once as an explicit release operation from the same image:

   ```bash
   docker run --rm --env-file /secure/path/production.env \
     ecommerce-api python manage.py migrate --noinput
   ```

2. Start or roll out web replicas only after the migration succeeds:

   ```bash
   docker run --rm --env-file /secure/path/production.env \
     -p 8000:8000 ecommerce-api
   ```

The web command starts Gunicorn directly as PID 1 and never runs migrations.
`SIGTERM` initiates Gunicorn's graceful shutdown, with a 30-second graceful
timeout. Failed migrations must stop the release; they must not be retried
independently by every web replica.

### JWT blacklist maintenance

SimpleJWT keeps outstanding and blacklisted refresh-token rows after the tokens
expire. Run its built-in cleanup command once per day against the production
database:

```bash
docker run --rm --env-file /secure/path/production.env \
  ecommerce-api python manage.py flushexpiredtokens
```

This is a periodic production maintenance operation, not a web-startup step.
Configure the selected deployment environment's scheduler to run it from the
same application image and with the same production settings and database
configuration as the web service. Exactly one scheduled runner should execute
each daily run; do not start it independently in every web replica. Scheduling
and failure alerting remain deployment responsibilities, so this repository
does not add Celery, cron configuration, or provider-specific infrastructure.

### Bale production operations

When Bale is the selected payment gateway, production must provide
`PAYMENT_GATEWAY_CLASS=apps.payments.bale.BaleGateway`, the secret
`BALE_BOT_TOKEN`, the production provider token, and the exact public HTTPS
`BALE_WEBHOOK_URL`. After the public route is reachable, register it as an
explicit one-off operation from the deployed image; rerun the command whenever
that URL changes:

```bash
docker run --rm --env-file /secure/path/production.env \
  ecommerce-api python manage.py set_bale_webhook
```

Webhook registration is never an image-build or web-startup action. If locally
durable Bale updates remain recoverable after an interruption, an operator can
run the existing idempotent recovery path on demand:

```bash
docker run --rm --env-file /secure/path/production.env \
  ecommerce-api python manage.py recover_bale_payments
```

Both commands require the same production settings, database, and Bale
credentials as the web service. Scheduling provider recovery speculatively is
not part of the current contract.

### Gunicorn and database runtime settings

- `PORT` selects the container listen port and defaults to `8000`.
- `WEB_CONCURRENCY` controls Gunicorn worker count and defaults to Gunicorn's
  conservative single worker. Set it only after measuring memory, CPU, request
  latency, and available PostgreSQL connections in the chosen environment.
- Gunicorn request and graceful-shutdown timeouts default to 30 seconds.
  `GUNICORN_CMD_ARGS` may override supported Gunicorn settings when a measured
  deployment requirement justifies it.
- Access and error logs go to stdout/stderr. The access format excludes query
  strings, referrers, and user-agent values.
- `DJANGO_DB_CONN_MAX_AGE` controls persistent PostgreSQL connection lifetime
  and defaults to `60` seconds. Set it lower than any provider-enforced idle
  connection timeout, or use `0` to disable connection reuse. Django connection
  health checks are enabled whenever production connections are reused.

No database pool size or Gunicorn worker formula is imposed because both depend
on the eventual database connection limit and container resources.
`DATABASE_URL` must provide a reachable PostgreSQL endpoint, production
credentials, database name, and any TLS/CA options required by that endpoint.
The deployment must budget PostgreSQL connections for every Gunicorn worker and
replica before increasing `WEB_CONCURRENCY` or replica count.

### Logging

Django application logs and Gunicorn access/error logs are written to process
stdout/stderr. The deployment platform must collect them, apply appropriate
retention and access controls, and alert on actionable failures. Logs must not
be treated as the authoritative order/payment audit record, and operators must
not add credentials, payment URLs, raw webhook payloads, provider transaction
identifiers, or customer PII to log enrichment.

### Static and uploaded media

`collectstatic` runs during the image build using non-secret, build-only Django
configuration. Production uses WhiteNoise with compressed, manifest-hashed
static files, so all web replicas serve the same immutable files included in the
image. Do not run `collectstatic` independently on each production replica.

Uploaded media under `MEDIA_ROOT` is different: the current filesystem storage
is not durable across container replacement and is not safe to treat as shared
storage across replicas. Before accepting durable production uploads, the
deployment must provide persistent shared media storage or the project must be
configured with an appropriate external storage backend. No storage provider is
selected here.

### Backup and restore

Database backup scheduling, encryption, retention, access control, and tested
restoration are deployment responsibilities. Backups must cover the production
PostgreSQL database; immutable static assets are rebuilt from the image and do
not require backup. If production accepts uploaded media, its selected durable
storage must have a compatible backup/versioning and restore plan. Operators
must periodically test restoration in an isolated environment rather than
assuming a successful backup job is recoverable. This repository intentionally
does not prescribe a database or storage provider's backup mechanism.

### Health probes

The image's Docker healthcheck calls the existing dependency-free liveness
endpoint inside the container:

```text
GET /api/v1/health/
```

The deployment platform should use `GET /api/v1/health/` for process/container
liveness and `GET /api/v1/health/readiness/` for readiness or traffic gating.
Readiness performs one PostgreSQL `SELECT 1`; neither probe contacts Bale or any
other third party. The exact liveness path is the only production endpoint
exempt from HTTP-to-HTTPS redirection so the container-internal probe does not
depend on reverse-proxy trust configuration; readiness and all normal endpoints
retain HTTPS enforcement. Configure the probe host consistently with
`DJANGO_ALLOWED_HOSTS`; invoke readiness through public HTTPS or the same trusted
forwarded-protocol path as normal traffic. A liveness success must not be used
to send traffic when readiness is failing.

## Manual Bale test-payment smoke test

This is a development-only end-to-end check, not a storefront. The smoke page
returns HTTP 404 whenever Django `DEBUG` is false. Its displayed result is only
the Bale client callback; the server-side webhook, transaction inquiry, and
atomic payment finalizer remain authoritative.

### Configure Bale and Django

1. Create a test bot with Bale's `@botfather` and put its token in
   `BALE_BOT_TOKEN`. Do not commit or paste that token into HTML, JavaScript, or
   documentation.
2. Set `BALE_PROVIDER_TOKEN=WALLET-TEST-1111111111111111`. This is Bale's
   documented wallet test token and does not transfer real money.
3. Set `PAYMENT_GATEWAY_CLASS=apps.payments.bale.BaleGateway` and keep
   `DJANGO_DEBUG=True` only in the development environment.
4. Expose the development server through a public HTTPS reverse proxy or tunnel.
   Bale accepts webhook port 443 (the normal HTTPS default) or 88. Add the public
   hostname to `DJANGO_ALLOWED_HOSTS`. If TLS terminates at a trusted reverse
   proxy, configure forwarded-protocol handling according to the production
   proxy notes above.
5. Set the exact public webhook endpoint, for example:

   ```dotenv
   BALE_WEBHOOK_URL=https://payments-test.example/api/v1/payments/bale/webhook/
   ```

   The `.example` hostname above is intentionally non-deployable and rejected by
   the registration command; replace it with the real public test hostname.

6. Configure the bot's Mini App URL in BotFather as the public development URL:
   `https://payments-test.example/api/v1/payments/bale/smoke/`.
7. Apply migrations and register the webhook explicitly (registration never
   happens during application startup):

   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py set_bale_webhook
   ```

### Create a payment through the normal application flow

Create an active category/product with whole-rial price and available stock in
the Django admin. Then use its slug through the public catalog and the normal
customer APIs. Replace values in angle brackets in these examples:

```bash
curl -X POST https://payments-test.example/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@example.com","password":"a-long-unique-password","first_name":"Test","last_name":"Customer","phone_number":"+989121234567"}'

curl -X POST https://payments-test.example/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@example.com","password":"a-long-unique-password"}'

curl -X POST https://payments-test.example/api/v1/account/addresses/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke","recipient_first_name":"Test","recipient_last_name":"Customer","recipient_phone_number":"+989121234567","province":"Tehran","city":"Tehran","address":"Test address","postal_code":"1234567890"}'

curl https://payments-test.example/api/v1/products/

curl -X POST https://payments-test.example/api/v1/cart/items/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"product_slug":"<product-slug>","quantity":1}'

curl -X POST https://payments-test.example/api/v1/checkout/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST https://payments-test.example/api/v1/orders/<order-id>/payments/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Copy only `payment_identifier` from the last response. Open the configured Mini
App inside Bale, paste that identifier into the smoke page, and select **Open
invoice**. The page passes the identifier unchanged to
`Bale.WebApp.openInvoice(...)` using Bale's official Mini App SDK. Complete the
wallet test payment. A page status of `paid`, `cancelled`, `failed`, or `pending`
is informational and never changes server state.

### Verify the authoritative result

Fetch `GET /api/v1/orders/<order-id>/` with the same bearer token and confirm the
order is `PAID`. For a successful test, database state must show:

- the `PaymentAttempt` is `SUCCESS` and has the provider transaction identity;
- the `Order` is `PAID`;
- its `InventoryReservation` rows are `CONSUMED`;
- each physical product's `stock_quantity` was decremented exactly once; and
- corresponding `BaleWebhookUpdate` rows reached `PROCESSED`.

Neither Bale credentials nor raw webhook payloads are persisted. The customer
API exposes the opaque invoice handoff value as `payment_identifier`, but does
not expose the bot/provider tokens, internal idempotency key, gateway name,
provider transaction identity, or webhook internals.
