# AGENTS.md

## Start Here

This repository is a production-oriented e-commerce monorepo. The Django/DRF
backend is feature-complete for the current portfolio scope, production-hardened,
and should be treated as a stable contract. The Next.js storefront is implemented
through checkout and payment handoff/result UX; the next planned milestone is
customer order history and order detail (Phase 5.3).

Read these sources before changing the areas they govern:

- `README.md`: local setup, production configuration, Docker/runtime lifecycle,
  security settings, health probes, maintenance commands, media caveats, and
  the manual Bale smoke flow.
- `FRONTEND_HANDOFF.md`: authoritative frontend integration guidance, API flow
  summaries, BFF security boundaries, media/payment behavior, and the current
  A/B/C/D frontend-readiness classification.
- `GET /api/schema/` and `GET /api/docs/`: generated OpenAPI contract and Swagger
  UI. Code and tests remain authoritative where OpenAPI cannot express a rule.
- Tests beside each Django app: executable specifications for permissions,
  concurrency, state transitions, data exposure, and error behavior.

Do not rely on historical milestones or chat context. Inspect the current code,
tests, migrations, settings, and relevant documents before implementing.

## Repository and Ownership Boundaries

```text
ecommerce/
├── backend/                 # Django application and Python tooling
│   ├── apps/                # accounts, products, carts, orders, payments, common
│   ├── config/              # URLs and split settings
│   ├── docker/              # backend container healthcheck
│   ├── requirements/
│   ├── Dockerfile
│   ├── gunicorn.conf.py
│   ├── manage.py
│   └── pyproject.toml
├── frontend/                # Next.js App Router storefront and same-origin BFF
├── compose.yaml             # repository-level local orchestration
├── .env.example             # repository-level environment contract
├── README.md
├── FRONTEND_HANDOFF.md
└── AGENTS.md
```

`frontend/` lives beside `backend/`. Keep its server-first App Router structure
and add Client Components only for real interaction. Do not add speculative
directories, dependencies, or monorepo tooling.

The backend uses Python 3.12, Django 5.2, DRF, PostgreSQL, SimpleJWT,
drf-spectacular, pytest/pytest-django, Ruff, Docker, and Gunicorn. PostgreSQL is
authoritative; never design implementation or concurrency behavior around
SQLite.

Run Compose from the repository root. Run direct Python tooling from `backend/`.
The Compose `web` service mounts `backend/` at `/app`.

## Change Discipline

- Prefer the smallest correct change. Do not add speculative endpoints,
  abstractions, dependencies, infrastructure, or generic cleanup.
- The backend contract is frozen unless a concrete correctness, security, or
  frontend-integration requirement proves a change is necessary. Do not redesign
  working APIs for style or premature frontend convenience.
- Trace a behavior through URLs, views/serializers, services, models, admin,
  settings, migrations, and tests before changing it. Follow existing patterns
  instead of creating parallel workflows.
- Keep HTTP parsing, authentication, permissions, throttling, and API error
  mapping in DRF. Put multi-model domain workflows in small explicit services.
- Use database constraints for important invariants where practical. Do not use
  signals for critical business workflows.
- Treat committed migrations as immutable. Add an incremental migration only
  for a real schema change and run migration consistency checks.
- Preserve public response fields, status codes, headers, ownership-hiding
  behavior, and OpenAPI output unless the task deliberately changes the API.
- Add tests for meaningful behavior, regressions, permissions, security
  boundaries, and concurrency—not merely to increase coverage.
- Preserve unrelated user changes in a dirty worktree.

## Frozen Backend Invariants

These are hard rules, not implementation suggestions.

### Identity, Authorization, and Data Exposure

- The custom `User` is the email-only authentication identity. Preserve email
  canonicalization, case-insensitive uniqueness, Django password hashing, and
  references through `AUTH_USER_MODEL`/`get_user_model()`.
- `CustomerProfile` contains customer state. Registration creates both records
  explicitly; staff/system users may lack a profile. An authenticated user
  without a profile must fail safely and never fall back to guest state.
- Derive ownership from the authenticated user. Never accept writable owner,
  privilege, lifecycle, or audit fields from clients. Scope querysets/lookups so
  cross-customer and unknown objects are indistinguishable where established.
- Addresses belong to a profile. At most one is default; zero is valid. The first
  address created through the API becomes default, and deleting it does not
  promote another.
- Non-superusers cannot grant privileges through User or Group admin. Admin
  access and `is_staff` alone never authorize domain/operator actions.
- SimpleJWT access/refresh, rotation, blacklisting, logout, and inactive-user
  behavior are established contracts. See `FRONTEND_HANDOFF.md` before touching
  auth flows.

### Catalog and Media

- Public catalog visibility requires an `ACTIVE` product and active direct
  category. Preserve the current API filters, pagination, snapshots, and N+1
  protections.
- Category parent mutations are serialized with the existing PostgreSQL
  transaction-level advisory lock and revalidated inside the transaction.
  `Category.save()` is authoritative; do not reintroduce `QuerySet.update`,
  `bulk_update`, or parented `bulk_create` bypasses. Preserve the direct
  self-parent database constraint.
- SKU uniqueness is case-insensitive. Product prices are positive whole IRR.
- A product has at most one primary image and deterministic image positions.
  Product/media ownership remains in Django. Production media storage is a
  deployment decision, not a frontend responsibility to redefine.

### Cart, Money, and Checkout

- Carts are persistent and `ACTIVE` or `CONVERTED`. They display current product
  data and never reserve or decrement stock.
- Guest carts use opaque `X-Cart-Token` bearer credentials. Resolve tokens only
  to active guest-owned carts. Authenticated requests use customer ownership and
  ignore guest credentials. Merge is explicit, atomic, consumes/rotates the
  guest credential, and must be replay-safe.
- Store currency is IRR. Use `Decimal`/`DecimalField`, never binary floats.
  API money values are whole-rial strings. Clients never determine authoritative
  prices or totals.
- Checkout atomically revalidates the customer, address, cart, products, prices,
  stock availability, and existing reservations. It creates a
  `PENDING_PAYMENT` order with immutable item/address/price snapshots and ACTIVE
  reservations, then converts the cart. Reservations claim availability but do
  not decrement physical stock.

### Order Lifecycle, Fulfillment, and Refunds

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

`DELIVERED`, `CANCELLED`, and `EXPIRED` are terminal. Do not add generic status
mutation paths.

- `PAID` and `EXPIRED` are compound system workflows. Fulfillment transitions
  are operator actions with an actor. Customer/operator cancellation is allowed
  only before `SHIPPED` and uses the domain service.
- Lifecycle timestamps on `Order` are written exactly once and are the source of
  truth. `OrderStatusHistory` is append-only with explicit customer/operator/
  system attribution.
- Command idempotency is actor/action-specific; a different actor or action must
  not be hidden as a successful replay.
- Cancelling `PENDING_PAYMENT` releases ACTIVE reservations, terminalizes a
  pending attempt, leaves stock unchanged, and needs no refund.
- Cancelling `PAID` or `PROCESSING` restores stock exactly once from aggregated
  order snapshots, preserves consumed reservations and successful payment
  history, and marks the refund `REQUIRED`.
- Refund tracking is only `NOT_REQUIRED`, `REQUIRED`, and `RESOLVED`. Resolution
  is a manual idempotent operator action. There is no automatic, gateway, or
  partial refund workflow.
- `Shipment` is one-to-one, created during `PAID -> PROCESSING`, editable only
  while processing, required for shipping, and immutable after shipment through
  normal application/admin paths.

### Payments and Bale

- `PaymentAttempt` is many-to-one with `Order`; at most one attempt may be
  `PENDING`. Attempts use durable unique idempotency keys.
- Persist payment intent before calling a gateway. Never hold long-lived
  database locks during network calls. Lock and revalidate authoritative state
  before persisting the result.
- Successful finalization decrements physical stock and consumes reservations
  exactly once. A successful attempt remains historical truth after later
  cancellation.
- Provider-authoritative late success must be recorded as `SUCCESS` even when
  the order is already `CANCELLED` or `EXPIRED`. The terminal order stays
  terminal, stock/reservations are not recreated or deducted, and refund status
  becomes `REQUIRED`.
- Client redirect/query/SDK callback data is never proof of payment. Bale
  webhook success requires provider inquiry and transaction identity checks
  before finalization. Webhooks remain direct Django/provider integrations, not
  BFF routes.
- Preserve initiation/verification idempotency, webhook replay handling, unique
  provider transaction identities, and the existing recovery path.
- Customer responses expose handoff URLs/identifiers only while an attempt is
  pending. Never expose or log gateway credentials, private references,
  provider transaction IDs, idempotency keys, raw webhook payloads, or internal
  payment data.

### Transactions and Concurrency

Commerce concurrency rules are mandatory:

- Use one outer `transaction.atomic()` for all-or-nothing domain work.
- Lock the aggregate/ownership row before trusting mutable state, then revalidate.
- Lock multi-row sets deterministically by primary key.
- Workflows touching the same data must use the established order:

  `Order -> PaymentAttempt (when needed) -> InventoryReservation -> Product (PK order)`

- Stock deduction and restoration are each exactly once.
- After savepoint rollback, account for stale in-memory Django instances without
  weakening locks held by the outer transaction.
- Real concurrency tests use separate PostgreSQL connections and assert final
  database invariants, not only response codes. Do not replace them with mocks
  or SQLite tests.

### Admin, Logging, and Recovery

- Django Admin is an operator interface, not a generic state editor. Orders,
  payments, reservations, refunds, shipment lifecycle, stock side effects, and
  audit rows must be changed only through existing domain-backed actions.
- Payment attempts and durable Bale webhook records are read-only in Admin.
  Catalog management and explicit stock correction must retain model validation,
  locking, and reservation-aware safeguards.
- Important committed lifecycle/payment/inventory outcomes are logged with
  `transaction.on_commit()`. Callbacks inside rolled-back savepoints must vanish.
  Logging must never change exception, transaction, locking, retry, or
  idempotency behavior.
- Log stable internal IDs and safe outcome categories, not secrets, auth headers,
  payment handoff values, idempotency keys, raw provider data, untrusted exception
  text, or unnecessary customer PII.
- Reuse the existing `recover_bale_payments` command and domain/admin recovery
  paths. Do not add generic fix-data commands without a demonstrated gap.

## Frontend Stage and Boundary

The current frontend uses:

- Next.js with App Router, TypeScript, and Tailwind CSS.
- `frontend/` beside `backend/`, developed through the root Docker Compose stack.
- Server-first rendering where useful; Client Components only for actual
  interactivity.
- A thin Next.js BFF/auth boundary. Browser credentials are kept out of
  localStorage and JavaScript-readable cookies.
- Browser-facing production topology is same-origin. Next.js calls Django with
  the existing JWT Bearer contract.
- No Redux, TanStack Query, Turborepo, Nx, or other infrastructure unless a
  concrete implementation need justifies it.

Implemented customer-facing scope currently includes the public catalog and
product detail, registration/login/logout and profile, customer addresses,
guest/authenticated cart with explicit login merge, authenticated checkout,
the created-order result, and payment initiation/return handling. Account order
history and general customer order-detail navigation are not implemented yet;
they are Phase 5.3. Do not infer completion from the post-checkout result route.

The BFF may handle rendering, secure HttpOnly browser cookies, CSRF/origin
protection for its cookie-authenticated mutations, server-side API calls,
serialized refresh-token rotation, guest-token cookie handling, and minimal
proxy/error mapping. It must not duplicate Django validation, pricing, stock,
cart merge, checkout, lifecycle, payment, refund, or webhook logic.

Follow `FRONTEND_HANDOFF.md` for endpoint sequences and frontend responsibilities.
In particular:

- keep JWTs and `X-Cart-Token` out of browser-readable storage;
- explicitly merge the guest cart after login;
- do not put personalized responses in shared caches;
- treat Django order state as payment truth;
- preserve structured errors and `429` behavior;
- do not infer public media/payment URLs from internal identifiers.

When frontend implementation uncovers friction, first determine whether it is a
demonstrated correctness, security, or required integration/contract gap; a BFF
responsibility; a deployment issue; or a nice-to-have. Change the frozen backend
only for a demonstrated gap in the first category.

## Production and Security Boundaries

Production configuration is environment-driven and provider-neutral. Detailed
variables and executable commands live in `README.md` and `.env.example`; do not
duplicate or drift them here.

- Production must fail fast on unsafe secrets, hosts, origins, or database
  configuration. Never weaken defaults for deployment convenience.
- Gunicorn serves plain HTTP in the container. TLS and a trustworthy forwarded
  protocol boundary are deployment responsibilities. Trust forwarding headers
  only when the ingress strips client values and overwrites them.
- CORS does not carry browser credentials. With the selected same-origin BFF,
  browser cookies terminate at Next.js and Django receives Bearer auth.
- DRF abuse throttles run before expensive side effects. Anonymous identity uses
  `REMOTE_ADDR` unless an exact trusted proxy count is configured. The current
  local-memory cache is acceptable only for the default single-process/runtime
  assumption; scale-out needs a shared cache or trusted ingress limiting.
- Migrations are an explicit single release step, never web startup. Static
  collection happens during image build. The web image starts Gunicorn directly.
- `/api/v1/health/` is cheap dependency-free liveness. Readiness at
  `/api/v1/health/readiness/` checks PostgreSQL only and returns a fixed 503 body
  on database failure. Do not add Bale or optional services to readiness.
- Run SimpleJWT `flushexpiredtokens` periodically from one scheduled production
  runner. Do not add it to web startup.

## Known and Deferred Decisions

Do not mistake these for defects without a concrete requirement:

- No deployment provider, public domain, durable media provider, database backup
  mechanism, or multi-replica cache has been selected. HSTS includeSubDomains and
  preload remain deployment-specific choices.
- Real Bale network validation depends on the selected deployment environment.
  The current customer handoff uses a Bale Mini App payment identifier, not a
  guaranteed standalone-browser payment URL.
- Customer order detail intentionally does not yet expose shipment tracking,
  full status history, lifecycle timestamps, stored refund status, or the
  payment deadline after the initial checkout response. See the D findings in
  `FRONTEND_HANDOFF.md`.
- The drf-spectacular `status` enum naming collision is known and non-blocking.
  Do not spend scope on it unless a generated frontend client demonstrates a
  concrete problem.
- Category children are derivable from the complete category list; there is no
  nested-tree endpoint.
- Automatic/partial refunds, returns/RMA, partial order cancellation,
  multi-shipment, warehouses/picking, carrier/label integrations, and unnecessary
  distributed infrastructure are out of scope until requirements change.

## Validation

Use the real PostgreSQL-backed environment. If the Compose web service is
running, prefer `docker compose exec web ...`; otherwise use
`docker compose run --rm web ...` from the repository root.

Run checks proportional to the change, with the full suite for backend behavior
changes when practical:

```text
pytest
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
ruff check .
ruff format --check .
git diff --check
```

Also run:

- `python manage.py spectacular --file /tmp/schema.yaml --validate` for API,
  serializer, URL, auth, or schema changes;
- production `check --deploy` for settings/security/runtime changes;
- production Docker build and health smoke checks for Docker/runtime/path changes;
- focused real-PostgreSQL concurrency tests for locking changes.

Documentation-only changes do not require the full backend suite. Always report
what ran, warnings, and anything intentionally not run.

## Git Rules

The user owns Git history and integration. The agent must never:

- commit, merge, push, pull, or rebase;
- create or switch branches;
- stash, reset, rewrite history, or discard user changes;
- stage files unless the user explicitly requests it.

Use read-only Git inspection freely. Keep changes narrowly scoped, inspect the
final diff/status, and suggest a Conventional Commit message without executing
it.
