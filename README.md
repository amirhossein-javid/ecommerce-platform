# E-commerce API

Production-oriented REST API built with Python 3.12, Django 5.2, Django REST
Framework, PostgreSQL, and Docker.

## Local setup with Docker

1. Copy `.env.example` to `.env` and replace the development secret.
2. Start the services:

   ```bash
   docker compose up --build
   ```

The API is available at `http://localhost:8000`. Useful endpoints:

- Health check: `GET /api/v1/health/`
- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

## Quality checks

Run these inside the web container:

```bash
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
docker compose run --rm web python manage.py check
```

## Production proxy settings

HSTS is disabled by default. Set `DJANGO_SECURE_HSTS_SECONDS` only after HTTPS
is working reliably for the production domain.

Set `DJANGO_TRUST_X_FORWARDED_PROTO=True` only when Django runs behind a trusted
reverse proxy that removes any client-supplied `X-Forwarded-Proto` header and
sets the header itself. Leave it disabled when that assumption does not hold.

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
