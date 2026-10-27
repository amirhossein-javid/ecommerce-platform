# AGENTS.md

## Start here

Naghsh-e Jahan is a single-store Persian RTL ecommerce monorepo. Treat the
implemented Django API and domain behavior as stable contracts. Inspect current
code and tests before changing behavior; do not infer it from chat history or
old verification counts.

Read the sources governing the work:

- [README.md](README.md): product scope, architecture, setup and verification.
- [FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md): API sequences, browser/BFF boundary,
  error contracts and deferred frontend capabilities.
- [OPERATIONS.md](OPERATIONS.md): configuration, proxy/throttle trust, runtime
  behavior, payment recovery and the development-only Bale smoke flow.
- [DEPLOYMENT_VPS.md](DEPLOYMENT_VPS.md): production topology, rollout, backup,
  restore and maintenance. [CHANGELOG.md](CHANGELOG.md) records release scope.
- App tests and generated `/api/schema/` and `/api/docs/`: executable behavior
  and API contract. Code/tests govern rules OpenAPI cannot express.
- [.github/workflows/ci.yml](.github/workflows/ci.yml): actual validation and
  dependency-security gates; do not substitute weaker checks.

## Structure and responsibility

- `backend/apps/`: accounts, products, carts, orders, payments and common.
  `backend/config/` contains URLs and split settings; `backend/requirements/`
  contains dependency inputs and committed, pinned installation locks.
- `frontend/`: Next.js App Router UI and same-origin BFF. Preserve Server
  Components for rendering and use Client Components for actual interaction.
- Root `compose.yaml` is development-only. `compose.production.yaml` and
  `deploy/` define the supported single-VPS deployment.
- Django owns credentials, permissions, prices, stock, checkout, order state,
  payment verification and moderation. The BFF owns browser cookies, origin
  checks, server-side requests, refresh coordination and safe error mapping.
- Keep HTTP parsing, authentication, throttling and API error mapping in DRF.
  Multi-model domain workflows belong in small explicit services. Do not move
  critical workflows into signals or add parallel generic mutation paths.

Run Compose from the repository root and direct Python tooling from `backend/`.
The development `web` service mounts that directory at `/app`.

## Change discipline

Prefer the smallest correct change. Preserve unrelated user work. Avoid broad
refactors, new dependencies, speculative endpoints, infrastructure and directory
structures without a demonstrated requirement. Do not add frontend state/query
frameworks or distributed services merely for possible future scale.

Trace affected URLs, views, serializers, services, models, Admin and tests.
Preserve response fields, status codes, headers, ownership hiding and schema
unless a concrete task deliberately changes them. Committed migrations are
immutable; add an incremental migration only for a real schema change.

## Identity, permissions and browser security

- `User` is the email-only identity. Preserve canonicalization, case-insensitive
  uniqueness, Django password hashing and `AUTH_USER_MODEL` references.
  `CustomerProfile` is customer state; staff may lack one. A missing profile
  must fail safely and never become a guest fallback.
- Derive ownership from authentication. Never accept writable owner, privilege,
  lifecycle or audit fields. Preserve indistinguishable cross-owner/unknown
  responses. Staff/Admin access alone does not authorize domain actions:
  retain explicit model permissions and non-superuser privilege restrictions.
- Addresses belong to a profile. At most one is default; zero is valid. The
  first API-created address is default; deleting it does not promote another.
- JWTs and guest-cart credentials stay server-side or in HttpOnly cookies,
  Secure in production, with existing SameSite/path settings. Never use browser
  storage. Preserve customer/management cookie separation and exact-origin
  checks for cookie-authenticated BFF mutations. Django receives Bearer tokens,
  not forwarded browser cookies; credentialed CORS stays disabled.
- Preserve SimpleJWT rotation, blacklisting, logout and inactive-user behavior.
  For refresh failures, only definitive rejection invalidates the session. 429
  preserves cookies and valid Retry-After; 5xx, transport/timeout and ambiguous
  responses preserve cookies and stop the protected request with a safe error.
  Never resume with unverified replacement tokens or automatically retry an
  ambiguous rotation within the same request. Coordination is process-local;
  do not claim cross-worker guarantees.
- Never expose or log credentials, auth headers, JWTs, guest tokens, payment
  handoffs, private references, provider transaction IDs, idempotency keys, raw
  webhook payloads, untrusted exception text or unnecessary customer PII.

## Catalog, cart and checkout invariants

- Public visibility requires an ACTIVE product and active direct category.
  Preserve filtering, pagination, bounded query counts and media ownership.
- Category parent writes use the existing PostgreSQL transaction advisory lock
  and revalidation in `Category.save()`. Do not bypass this through update,
  bulk_update or parented bulk_create. Preserve the self-parent constraint.
- Preserve case-insensitive SKU uniqueness, positive whole-IRR prices,
  nonnegative stock, one primary image and deterministic image positions.
- Carts are persistent ACTIVE/CONVERTED records and never reserve or deduct
  physical stock. Guest credentials resolve only active guest-owned carts.
  Authenticated requests ignore guest credentials; explicit merge is atomic,
  consumes/rotates the guest credential and preserves replay protection.
- Use Decimal for authoritative money. API amounts are whole-rial strings;
  clients never determine prices or totals.
- Checkout atomically revalidates customer/address/cart/catalog/availability,
  creates PENDING_PAYMENT with immutable item/address/price snapshots and ACTIVE
  reservations, then converts the cart. Reservations claim availability without
  decrementing physical stock.
- Reviews allow one existing review per customer/product: integer rating 1â€“5,
  required text, server-derived author and PENDING status. Customers may read
  their status and delete, not edit; deletion permits a fresh pending review.
  Public data/aggregates include APPROVED only. Pending moderation requires the
  change permission; each official reply is one-to-one and separately permission
  checked. Preserve the independent static homepage testimonials.

## Order, fulfillment and payment invariants

Allowed order transitions are exactly:

```text
PENDING_PAYMENT -> PAID | CANCELLED | EXPIRED
PAID            -> PROCESSING | CANCELLED
PROCESSING      -> SHIPPED | CANCELLED
SHIPPED         -> DELIVERED
```

DELIVERED, CANCELLED and EXPIRED are terminal. PAID and EXPIRED are compound
system workflows. Customer/operator cancellation uses the domain service and
is permitted only before SHIPPED. Preserve these rules:

- Lifecycle timestamps are written once. Status history is append-only with
  explicit customer/operator/system attribution. Replays are actor/action
  specific and must be proven by locked current state and persisted history.
- Pending cancellation releases ACTIVE reservations, fails a pending attempt,
  leaves physical stock unchanged and needs no refund. Paid/processing
  cancellation restores aggregated snapshot stock exactly once, preserves
  consumed reservations and successful payment history, and requires a refund.
- Refund states are NOT_REQUIRED, REQUIRED and RESOLVED. Resolution is manual,
  operator-attributed and idempotent; no automatic, partial or gateway refund.
- Shipment is one-to-one, created during PAID -> PROCESSING, editable only while
  processing, required for shipping and immutable afterward in normal paths.
- At most one payment attempt per order is PENDING. Persist intent and durable
  idempotency keys before provider calls; never hold long-lived DB locks across
  network calls. Lock and revalidate before persisting the provider result.
- Successful finalization deducts stock and consumes reservations exactly once.
  Provider-authoritative late success remains SUCCESS even for a terminal order:
  keep that order terminal, do not deduct/recreate inventory, require refund.
- Redirect/query/SDK callback data never proves payment. Bale webhook success
  needs provider inquiry and transaction identity checks. Retain webhook replay
  handling, durable recovery records and `recover_bale_payments`; do not add
  speculative repair commands or BFF webhook routes.

## Transactions and Admin

Use one outer atomic transaction per all-or-nothing domain operation. Lock the
aggregate/ownership row before trusting mutable state and revalidate under lock.
Preserve existing serialization and deterministic PK ordering; workflows sharing
commerce rows use `Order -> PaymentAttempt (when needed) ->
InventoryReservation -> Product`.
After savepoint rollback, account for stale in-memory instances without releasing
or weakening outer locks. Stock deduction and restoration are each exactly once.

Django Admin is an operator interface. Order/payment/reservation/refund lifecycle
and stock side effects use domain-backed actions; attempts and durable webhook
records remain read-only. Preserve reservation-aware catalog/stock validation.
Changelist forms may contain stale instances: partial status saves must not write
omitted inventory fields. Full product stock corrections retain their lock.

Log committed lifecycle/inventory/payment outcomes through `transaction.on_commit()`.
Rolled-back callbacks must vanish. Use stable internal IDs and safe outcome
categories; logging must not change transaction, retry or exception behavior.

## Runtime and release boundaries

The production stack has one Caddy container with public HTTPS and an internal
8080 BFF listener. Only public Caddy publishes host ports. Keep Django's HTTPS
redirect enabled; retain host/scheme normalization and the validated client-IP
handoff for anonymous throttles. Revisit trust configuration before adding a CDN,
proxy or published frontend. Do not weaken production secret/host/origin/DB
validation or change the supported BFF upstream directly to Gunicorn.

Production uses non-root images, image-build static collection, explicit release
migrations and a persistent single-VPS media volume. Keep JWT cleanup as one
host-scheduled maintenance job, separate from web startup.
Liveness is dependency-free; readiness checks PostgreSQL only. Do not introduce
Bale into health probes. Shared throttling/refresh coordination needs an explicit
decision before scaling beyond the current process-local assumptions.

Do not claim public deployment, live Bale success, backup restoration or CI on a
revision without evidence. Provider-specific off-server backups, monitoring and
capacity acceptance remain deployment work. Deferred product fields and larger
commerce workflows in FRONTEND_HANDOFF/CHANGELOG are not defects to implement
without a concrete request.

## Validation

Use PostgreSQL, never SQLite, for database behavior and separate connections for
real concurrency tests. Release verification uses disposable PostgreSQL isolated
from project/production databases and persistent volumes. Do not restart or prune
shared infrastructure; inspect identities before cleaning task-owned resources.
Check available disk space before large installs/builds and stop before exhaustion.

Run checks proportional to the change; backend behavior changes normally warrant
the full suite. In a correctly configured backend environment, run:

```bash
pytest
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
ruff check .
ruff format --check .
```

Also validate OpenAPI with `python manage.py spectacular --file /tmp/schema.yaml --validate`
for API/schema/auth changes; run production security checks with the
CI production environment for settings/security changes. Docker/runtime changes
need production builds and health smoke checks. If a disposable image's `/app`
is not writable, put Ruff/pytest caches in `/tmp` without changing check semantics.

Frontend checks are `npm run lint`, `npm run typecheck`, `npm test`,
`npm run test:integration` and `npm run build`. Use `npm ci` and the committed
lockfile; CI additionally checks TypeScript from a clean generated state.
Security gates are the exact npm runtime/full and strict Python-lock audits in
CI. Do not add exceptions, disable TLS verification or treat audit-service errors
as a clean audit. Do not update locks during a verification-only task.

Always review the final diff, run `git diff --check`, and report commands/results,
warnings and checks not run. Documentation-only edits do not need full suites;
validate links, command references and any diagrams instead.

## Git safety

The user owns Git history and integration. Do not commit, push, pull, merge,
rebase, amend, create/switch branches, stash, reset, tag, release or discard user
changes without explicit authorization for that action. Do not stage files unless
explicitly requested. Read-only Git inspection is allowed. Keep unrelated user
changes intact and never present local checks as successful GitHub Actions runs.
