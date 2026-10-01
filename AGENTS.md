# AGENTS.md

## Project and Stack

Production-oriented e-commerce backend using Python 3.12, Django 5.2,
Django REST Framework, PostgreSQL, SimpleJWT, pytest/pytest-django, Ruff,
drf-spectacular, Docker Compose, and Gunicorn.

- Django apps live under `apps/`.
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
- Admin operator actions must call lifecycle services and preserve locking,
  audit history, and actor attribution; admin must not write lifecycle state
  directly.

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

Use the real PostgreSQL-backed environment. Run commands in the Compose `web`
service with `docker compose exec web ...` when it is running, or
`docker compose run --rm web ...` otherwise.

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

## Git and Change Discipline

- Codex must never commit, push, merge, rebase, create/switch branches, stash,
  rewrite history, or otherwise alter Git history. The user manages Git.
- The project uses feature branches merged with `--no-ff` and Conventional
  Commits.
- Keep tasks narrowly scoped, preserve unrelated work, inspect the final diff,
  and report changes, checks, and limitations concisely.

## Completed Phases

- Phase 1 — Foundation: complete
- Phase 2 — Accounts/Auth: complete
- Phase 3 — Products/Catalog: complete
- Phase 4 — Shopping/Orders: complete
- Phase 5 — Payments/Bale: complete
- Phase 6 — Fulfillment/Order Lifecycle: complete; merged to `main` via
  `Merge branch 'feature/fulfillment'`

## Remaining Backend Roadmap

### Phase 7 — Store Operations / Admin / Observability

- Production-safe Django admin/operator workflows
- Operational visibility for orders, payments, refunds, and inventory
- Logging, health/readiness, and recovery improvements where justified
- Permission, security, and admin hardening
- Avoid unnecessary dashboards and infrastructure

### Phase 8 — Production Deployment and Final Hardening

- Production settings, security, deployment, container, and runtime checks
- Environment/secrets and applicable static/media strategy
- Final API/schema/security/performance review
- Real Bale network end-to-end testing when a deployment environment exists
- Frontend-facing API contract review

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
