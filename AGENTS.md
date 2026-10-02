# AGENTS.md

## Project and Stack

Production-oriented e-commerce backend using Python 3.12, Django 5.2,
Django REST Framework, PostgreSQL, SimpleJWT, pytest/pytest-django, Ruff,
drf-spectacular, Docker Compose, and Gunicorn.

- The Django backend lives under `backend/`; its apps live under `backend/apps/`.
- Settings are split into `base.py`, `development.py`, and `production.py`.
- PostgreSQL is authoritative. Do not design or test behavior specifically for
  SQLite.
- Prefer simple, explicit Django/DRF patterns and the smallest correct change.

Before implementing, inspect the relevant models, services, migrations,
serializers, views, URLs, tests, and settings. Follow existing conventions
instead of creating parallel abstractions.

## Development Rules

- Understand and preserve domain rules before changing implementation.
- Put multi-model workflows in small, explicit domain services. Keep HTTP
  parsing, authentication, permissions, and API error mapping in DRF.
- Use database constraints for important invariants when practical.
- Do not use signals for important business workflows.
- Add tests for meaningful behavior, regressions, permissions, and security
  boundaries; do not add tests merely to increase coverage.
- Avoid speculative layers, dependencies, infrastructure, and refactors.
- Do not silently change public API behavior.
- Treat committed migrations as immutable. Add incremental migrations and run
  migration consistency checks after model changes.

## Transaction and Concurrency Rules

These rules are mandatory for commerce workflows:

- Use one outer `transaction.atomic()` boundary for all-or-nothing domain work.
- Lock the aggregate/ownership row before trusting mutable state, then
  revalidate after acquiring the lock.
- Lock multi-row sets deterministically by primary key.
- Workflows touching the same data must use compatible lock ordering.
- Established lifecycle lock order is:

  `Order -> PaymentAttempt (when needed) -> InventoryReservation -> Product (PK order)`

- Never call a gateway or other network API while holding long-lived database
  locks.
- Stock deduction and restoration must each be exactly once.
- After savepoint rollback, account for stale in-memory Django model instances;
  refresh state safely without weakening held aggregate locks.
- Concurrency tests must use real, separate PostgreSQL connections and assert
  final database invariants, not only response codes.

## Accounts and Addresses

- The custom `User` is the authentication identity and uses email-only login.
  Preserve email canonicalization, case-insensitive uniqueness, Django password
  hashing, and cross-app references through `AUTH_USER_MODEL`/`get_user_model()`.
- `CustomerProfile` holds customer-specific state. Public registration creates
  both `User` and `CustomerProfile` explicitly; staff/system users may lack a
  profile.
- Authenticated users without a `CustomerProfile` must fail safely and must
  never fall back to guest credentials or state.
- Customer-owned resources derive ownership from the authenticated user. Never
  trust client-supplied ownership fields, and enforce isolation at queryset or
  object lookup level.
- Addresses belong to `CustomerProfile`. At most one may be default; zero is
  valid. The first address created by application workflows becomes default.
  Deleting a default does not promote another address.
- Saved addresses are mutable customer data, not historical order snapshots.

## Catalog

- `Category` is hierarchical and protects against self-parenting and ancestor
  cycles.
- `Product` lifecycle is `DRAFT` / `ACTIVE` / `ARCHIVED`; public visibility must
  respect product and category state.
- SKU uniqueness is case-insensitive.
- `ProductImage` enforces at most one primary image per product and deterministic
  positions.

## Cart

- Carts are persistent and have `ACTIVE` / `CONVERTED` state.
- Guest carts use opaque `X-Cart-Token` bearer credentials. Scope token lookups
  to eligible guest-owned records and rotate or invalidate tokens when state is
  claimed or consumed.
- Authenticated ownership is isolated. Guest-to-authenticated merging is an
  explicit workflow; never use guest credentials as authenticated ownership
  proof.
- A cart does not reserve or decrement stock and displays current authoritative
  product prices.

## Orders and Checkout

- Orders snapshot product identity, unit prices, totals, and shipping address;
  historical reads must not depend on later product, price, or address changes.
- Prices and totals are computed from authoritative server-side data.
- Checkout atomically creates a `PENDING_PAYMENT` order, order items, and ACTIVE
  inventory reservations. The cart becomes `CONVERTED` only after success.
- Reservations represent availability claims and do not decrement physical
  stock.

## Money

- Store currency is IRR.
- Use `Decimal`/`DecimalField`, never binary floats.
- Amounts must be whole rials and are protected by validation and database
  constraints.
- Money in APIs is represented as whole-rial strings. Clients never determine
  authoritative prices or totals.

## Payments

- `PaymentAttempt` is many-to-one with `Order`; an order may have at most one
  PENDING attempt. Attempt states are `PENDING`, `SUCCESS`, and `FAILED`.
- Each attempt has a durable unique idempotency key. Create durable intent before
  the gateway call, perform the network call outside long transactions, then
  lock and revalidate before persisting its result.
- Successful finalization decrements physical stock exactly once and changes
  ACTIVE reservations to CONSUMED.
- Late success cannot revive an expired or cancelled order.
- Bale initiation, webhook handling, verification/inquiry, idempotency, and
  local recovery are implemented. Keep webhook input and gateway errors
  sanitized.
- Customer payment URLs/identifiers are exposed only while the attempt is
  PENDING. Do not expose private gateway references, credentials, idempotency
  keys, or internal payment data.
- A `SUCCESS` attempt remains historical truth when a paid order is later
  cancelled.

## Order Lifecycle

Allowed transitions are exactly:

```text
PENDING_PAYMENT -> PAID
PENDING_PAYMENT -> CANCELLED
PENDING_PAYMENT -> EXPIRED
PAID            -> PROCESSING
PAID            -> CANCELLED
PROCESSING      -> SHIPPED
PROCESSING      -> CANCELLED
SHIPPED         -> DELIVERED
```

`DELIVERED`, `CANCELLED`, and `EXPIRED` are terminal.

- PAID and EXPIRED are compound SYSTEM workflows, not generic/public
  transitions.
- PROCESSING, SHIPPED, and DELIVERED are OPERATOR actions and require an actor
  user.
- A CUSTOMER owner or OPERATOR may cancel only before SHIPPED.
- `OrderStatusHistory` is append-only application audit history with explicit
  CUSTOMER / OPERATOR / SYSTEM attribution.
- Lifecycle timestamps are source-of-truth fields on `Order` and are written
  exactly once.
- Idempotency is command-specific: a duplicate command by the same authorized
  actor is safe, but a different actor/action must not be hidden as success.

### Cancellation and Refund Tracking

- Cancelling `PENDING_PAYMENT` releases ACTIVE reservations, terminalizes a
  PENDING payment attempt, leaves physical stock unchanged, and sets refund
  status to `NOT_REQUIRED`.
- Cancelling `PAID` or `PROCESSING` restores physical stock exactly once from
  authoritative aggregated `OrderItem` quantities. CONSUMED reservations and
  `PaymentAttempt.SUCCESS` remain unchanged; refund status becomes `REQUIRED`.
- Refund tracking states are `NOT_REQUIRED`, `REQUIRED`, and `RESOLVED`. Manual
  resolution records operator and timestamp and is idempotent for that operator.
- There is no automatic/gateway refund, partial refund, or separate Refund
  domain yet.

### Fulfillment

- `Shipment` is one-to-one with `Order` and is created atomically during
  `PAID -> PROCESSING`.
- Carrier and tracking number may be edited only while PROCESSING and are
  required before SHIPPED.
- Shipment data is immutable after SHIPPED through normal application/admin
  paths.
- Lifecycle timestamps on `Order`, not `Shipment`, are the fulfillment source
  of truth.

## Store Operations and Observability

### Django Admin and Operator Boundaries

- Django Admin is an operator interface, not a generic state editor. Order,
  payment, reservation, refund, shipment lifecycle, lifecycle-driven stock,
  and audit state must not be mutated directly through admin model forms or
  bulk updates.
- Fulfillment, cancellation, and refund actions must delegate to the existing
  domain services so locking, exactly-once inventory behavior, audit history,
  idempotency, and actor attribution remain intact.
- Admin access or `is_staff` alone does not authorize privileged operations.
  Actions require the relevant Django model permission, and non-superusers must
  not grant privileges or manage privileged accounts.
- Protect operational records from unsafe add/delete/change paths. Payment
  attempts and durable Bale webhook records are read-only in Admin; orders are
  changed only through explicit domain-backed actions. Shipment details may be
  edited only while the order is PROCESSING and remain protected by the model's
  locked invariant checks.
- Catalog management and explicit physical-stock corrections may use the
  validated, locked Product Admin workflow; stock must not be reduced below
  unexpired ACTIVE reservations or used to bypass payment/cancellation services.
- Do not expose gateway credentials, private references, provider transaction
  identifiers, idempotency keys, payment URLs/tokens, raw webhook payloads, or
  unnecessary customer/payment data in Admin.
- Operational visibility is derived from authoritative domain fields using
  list displays, filters, annotations, and read-only indicators. Do not add
  persistent attention flags, arbitrary "stuck" timeouts, or per-row queries;
  add query-count tests where changelist N+1 regressions are plausible.

### Application Logging

- Use Python/Django logging for meaningful lifecycle, cancellation, inventory,
  payment, Bale recovery, refund, and fulfillment outcomes. Prefer stable IDs,
  actor type/ID, previous/new state, outcome, and a safe failure category.
- Important committed successes must be logged with `transaction.on_commit()`;
  callbacks scheduled inside savepoints must disappear on rollback. Logging
  must not change exception, transaction, locking, retry, or idempotency
  behavior and must not duplicate `OrderStatusHistory` as another audit system.
- Use INFO for important successful transitions, WARNING for recoverable or
  attention-worthy conditions, and ERROR for unexpected failures at the layer
  with useful domain context. Do not swallow exceptions merely to log them or
  emit duplicate stack traces across layers.
- Never log secrets, credentials, authorization headers, payment URLs/tokens,
  idempotency keys, raw gateway/webhook payloads, private provider references or
  transaction identifiers, untrusted exception text, or unnecessary customer
  PII such as email, phone, and address data.

### Health and Recovery

- `GET /api/v1/health/` is the unauthenticated liveness probe. It reports that
  Django can serve a request and must remain cheap and dependency-free.
- `GET /api/v1/health/readiness/` is the unauthenticated readiness probe. It
  performs one minimal `SELECT 1` against the authoritative PostgreSQL database
  and returns HTTP 503 with a fixed, non-sensitive body when unavailable.
- PostgreSQL is currently the only request-serving readiness dependency. Do not
  call Bale or other third parties from readiness, and do not add Redis, cache,
  or Celery checks unless the architecture later makes them required to serve
  normal requests.
- Existing recovery paths are the `recover_bale_payments` management command,
  domain-backed Admin lifecycle/cancellation/refund actions, and payment service
  retry/expiry handling. Recovery must reuse those services and invariants.
  Do not add speculative commands or generic state-editing/fix-data tools; add
  the smallest idempotent command only for a demonstrated operational gap.

## API and Data Rules

- Authentication endpoints use `/api/v1/auth/`; authenticated customer account
  resources use `/api/v1/account/`; commerce/catalog endpoints use `/api/v1/`.
- Use DRF validation consistently and keep writable/read-only fields explicit.
- Do not leak object existence across ownership boundaries or expose internal
  ownership/privilege fields through writes.
- Keep OpenAPI output accurate when endpoints change.
- Use `select_related()`/`prefetch_related()` for nested data and query-count
  tests where N+1 regressions are plausible.
- Historical commerce data comes from immutable snapshots; current catalog and
  cart data use authoritative live product data where appropriate.

## Tests and Verification

Use the real PostgreSQL-backed environment. Run Compose commands from the
repository root in the `web` service with `docker compose exec web ...` when it
is running, or `docker compose run --rm web ...` otherwise. Run direct Python
tooling from `backend/`.

After implementation, run the relevant suite:

- `pytest`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate --check`
- `ruff check .`
- `ruff format --check .`
- `git diff --check`

For API changes also run:

- `python manage.py spectacular --file /tmp/schema.yaml --validate`

Run production/security checks when the change affects those areas.

The existing drf-spectacular enum naming collision warning is known and
non-blocking. Do not spend scope on it unless future work introduces or exposes
a concrete schema problem.

## Git and Change Discipline

- Codex must never commit, push, merge, rebase, create/switch branches, stash,
  rewrite history, or otherwise alter Git history. The user manages Git.
- The project uses feature branches merged with `--no-ff` and Conventional
  Commits.
- Keep tasks narrowly scoped, preserve unrelated work, inspect the final diff,
  and report changes, checks, and limitations concisely.

## Current State and Roadmap

Phases 1–7 are complete. Phase 8 — Production Deployment & Final Hardening —
is the only remaining backend phase:

- Finalize production settings, secrets, HTTPS/security behavior, deployment,
  container/runtime behavior, and production validation.
- Perform the final backend security, API/schema, performance, and concurrency
  review.
- Run real Bale network end-to-end validation in the selected deployment
  environment.
- Review and hand off the frontend-facing API contract after the frontend stack
  is selected.

No deployment provider has been selected. Keep production configuration
provider-neutral and environment-driven until that decision is made. HSTS and
deployment-specific HTTPS hardening are intentionally deferred to Phase 8. The
frontend stack is also not finalized and must be decided before the final
frontend-facing audit and handoff.

After Phase 8, the backend is considered feature-complete for the portfolio
scope and frontend implementation begins. Keep backend APIs stable unless a
real integration problem requires change; do not add premature frontend hacks.

## Explicitly Out of Scope

Unless future requirements justify them:

- Automatic or partial refunds
- Returns/RMA
- Partial order cancellation
- Multi-shipment
- Warehouse/picking systems
- Carrier or shipping-label integrations
- Unnecessary distributed infrastructure
