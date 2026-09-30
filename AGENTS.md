# AGENTS.md

## Project

Production-oriented e-commerce backend using Python 3.12, Django 5.2, Django
REST Framework, PostgreSQL, pytest/pytest-django, Ruff, drf-spectacular,
Docker Compose, and Gunicorn.

Django apps live under `apps/`.

Settings are split into `base.py`, `development.py`, and `production.py`.

PostgreSQL is the authoritative database. Do not design or test behavior specifically for SQLite.

## Architecture

Prefer simple, explicit Django/DRF patterns.

- Keep business rules and ownership boundaries explicit.
- Use database constraints for important invariants when practical.
- Put multi-model state transitions in small, explicit domain services; keep HTTP
  parsing, authentication, and API error mapping in the DRF layer.
- Use one outer `transaction.atomic()` boundary for all-or-nothing workflows.
- For concurrency-sensitive workflows, lock ownership/aggregate rows before
  dependent rows, lock multi-row sets in deterministic primary-key order, and
  revalidate mutable state after acquiring locks. Keep locks targeted and use a
  consistent order across workflows that touch the same rows.
- Do not use signals for important business workflows.
- Do not introduce service/repository layers without a concrete benefit.
- Do not add infrastructure or dependencies without a current requirement.
- Avoid premature abstractions and speculative features.

Before implementing, inspect related models, migrations, serializers, views, URLs, tests, and settings.

Follow existing project conventions instead of creating parallel patterns.

## Accounts

The custom `User` is the authentication/authorization identity.

- Email is the login identifier.
- Preserve email canonicalization and case-insensitive uniqueness.
- Always use Django password hashing APIs.
- Across app boundaries, reference users through `settings.AUTH_USER_MODEL` or
  `get_user_model()`.
- `CustomerProfile` represents customer-specific data.
- Public customer registration explicitly creates both `User` and `CustomerProfile`.
- Staff/system users may exist without `CustomerProfile`.
- Important account creation workflows must not rely on signals.

Customer-owned resources must derive ownership from the authenticated user.

Never trust client-supplied ownership fields such as `user` or `customer_profile`.

Cross-customer object access must be prevented at queryset/object lookup level.

Authenticated users without a `CustomerProfile` must fail safely and must never
fall back to guest credentials or guest-owned state.

Treat opaque guest tokens as bearer credentials: scope lookups to eligible
guest-owned records, never use them as authenticated ownership proof, and rotate
or invalidate them when guest state is claimed or consumed.

## Addresses

`CustomerProfile` owns addresses.

- A customer may have multiple addresses.
- At most one address may be default.
- Zero default addresses is valid.
- Application workflows that create a customer's first address must make it
  default; model `save()` does not do this automatically.
- Default-address changes must preserve the database invariant and concurrency behavior.
- Deleting a default address does not automatically promote another address.
- Saved addresses must not be treated as historical order snapshots.

## API

Authentication endpoints live under:

`/api/v1/auth/`

Authenticated customer resources live under:

`/api/v1/account/`

Use DRF validation and serializers consistently.

Keep writable and read-only fields explicit.

Do not expose internal ownership or privilege fields through API writes.

Use appropriate HTTP status codes without leaking unnecessary account or object-existence information.

Keep OpenAPI output accurate when endpoints change.

Use `select_related()`/`prefetch_related()` for nested response data and add
query-count tests when an endpoint could regress into N+1 queries.

## Commerce Data Integrity

- Use `Decimal`/`DecimalField` for money; never use binary floats.
- Calculate prices and totals server-side from authoritative domain data. Do not
  trust client-supplied monetary values.
- Size monetary fields for valid multiplication and aggregation ranges, and back
  important nonnegative/arithmetic invariants with database constraints.
- Historical records must read mutable product, price, and address data from
  immutable snapshots rather than current related objects.

## Migrations

Treat committed migrations as immutable history.

- Do not edit or replace existing migrations unless explicitly requested.
- Create incremental migrations for schema changes.
- Do not reset the database or migration history unless explicitly justified and requested.
- Run migration consistency checks after model changes.

## Tests

Use the real PostgreSQL-backed test environment.

Run project commands in the Compose `web` service: use
`docker compose exec web ...` when it is running, or
`docker compose run --rm web ...` otherwise.

Add tests for meaningful behavior, regressions, permissions, invariants, and security boundaries.

For concurrency-sensitive database behavior, use real transaction/concurrency
tests when needed. Such tests must use separate database connections and should
assert the final invariant, not merely that both calls returned.

Do not add tests solely to increase coverage numbers.

After implementation, run the relevant project validation suite:

- `pytest`
- `python manage.py check`
- `ruff check .`
- `ruff format --check .`
- `makemigrations --check --dry-run`
- `migrate --check`
- `git diff --check`

For API changes, also run
`python manage.py spectacular --file /tmp/schema.yaml --validate`. Run
production/security checks when the change affects those areas.

## Change Discipline

Keep each task narrowly scoped.

- Do not implement unrelated features.
- Do not perform speculative refactors.
- Do not silently change public API behavior.
- Do not change models or migrations unless required by the task.
- Reuse existing validators, constraints, and conventions.
- Prefer the smallest correct change over a broad redesign.

If inspection reveals a serious security, data-integrity, or architectural conflict, report it before expanding scope.

Otherwise, implement the requested change and validate it.

## Git

Do not commit, push, merge, rebase, create/switch branches, or rewrite Git history unless explicitly requested.

The developer handles normal Git workflow.

Before finishing a task, review the diff for unrelated changes.

Report changes, checks, and remaining limitations concisely.
