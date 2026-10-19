# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-17

This is the first source release of the Naghsh-e Jahan ecommerce platform. It
has been validated locally but has not yet been deployed to a public production
environment.

### Added

- A Django 5.2 and Django REST Framework API backed by PostgreSQL, with
  email-only accounts, JWT rotation and blacklisting, customer profiles, owned
  addresses, a public catalog, product media, reviews, and official store
  replies.
- Guest and authenticated carts, explicit replay-safe cart merging,
  transactional checkout, inventory reservations, immutable order snapshots,
  customer order history and cancellation, operator fulfillment, shipment, and
  manual refund-resolution workflows.
- Persisted, idempotent payment attempts with Bale initiation, provider inquiry,
  webhook processing, late-success handling, and an operator recovery command.
- A Persian RTL Next.js App Router storefront covering catalog discovery,
  authentication, account and address management, cart, checkout, payment
  handoff/result handling, orders, and customer reviews.
- A focused Next.js operator dashboard for order metrics, fulfillment, refund
  resolution, review moderation, and official replies, alongside the protected
  Django Admin back office.
- A same-origin BFF that keeps customer and operator JWTs and guest-cart tokens
  in scoped HttpOnly cookies, enforces exact-origin checks for mutations,
  serializes refresh rotation, and preserves authoritative Django errors and
  order state.
- Local and production Docker images and Compose definitions, Caddy TLS and
  trusted-proxy routing for the documented single-VPS topology, health and
  readiness probes, explicit migration and maintenance commands, and backup and
  restore helpers.
- PostgreSQL-backed backend tests, frontend unit tests, and BFF integration
  tests that exercise real route handlers through a running Next.js server and
  a controlled HTTP upstream, plus reproducible Python and npm dependency
  locks, OpenAPI validation, and GitHub Actions release gates.

### Security

- Enforced ownership-scoped access, explicit operator permissions, secure JWT
  and guest-cart handling, payment and lifecycle idempotency, transaction and
  row-locking rules, safe logging, production setting validation, and
  reservation-aware stock consistency.
- Preserved anonymous client identity across the trusted Caddy, Next.js BFF,
  and Django proxy boundary without accepting browser-supplied forwarding
  headers; authenticated throttles remain keyed by user identity.
- Added Python production/development vulnerability audits and separate npm
  runtime/development audits to CI. Production `npm audit --omit=dev` reports
  zero vulnerabilities.
- Temporarily accepted `GHSA-vfj7-8cjw-p6xm` as a development-only npm risk.
  The affected chain is `eslint-config-next` -> `@next/eslint-plugin-next` ->
  `fast-glob` -> `micromatch` -> `braces`. No compatible patched release was
  available at the time of review without an incompatible Next.js downgrade.
  CI accepts only this exact chain and must fail for any unrelated, changed, or
  newly introduced advisory.

### Validation

- The latest local release-hardening runs completed with 761 backend tests, 68
  frontend unit tests, and 5 BFF integration test results passing.
- Local Ruff lint and format checks, Django system and deployment-security
  checks, migration consistency, OpenAPI validation, ESLint, TypeScript checks
  from a clean generated state, and the Next.js production build passed.
- Clean locked dependency installation, Python production/development audits,
  the npm production audit, and backend/frontend production Docker image builds
  passed locally.
- GitHub Actions is configured to repeat these release gates on pushes to
  `main` and pull requests targeting `main`. No successful GitHub-hosted run is
  claimed by this release documentation because no run evidence was available
  during the review.

### Not yet production-verified

- The platform has not been publicly deployed. Public DNS, TLS operation,
  external monitoring, and a provider-specific off-server backup and restore
  drill remain deployment acceptance work.
- Live Bale payment success, provider inquiry, webhook delivery/replay, and the
  full Mini App return flow have not been verified against the real provider.
  No real payment is claimed to have been completed.
- Browser-based visual validation of RTL presentation and responsive layouts at
  360 px, 390 px, and desktop widths has not been completed. A browser-based
  accessibility audit has also not been completed.
- Durable production media storage, real production secrets, and capacity
  sizing depend on the selected hosting environment.

### Out of scope for 1.0.0

- Automatic, gateway-driven, or partial refunds; returns/RMA; partial order
  cancellation; multi-shipment; warehouse/picking workflows; and carrier or
  label integrations.
- Multi-replica cache and media architecture, provider-specific managed
  infrastructure, and deployment automation beyond the documented single-VPS
  tooling.
- Additional customer order-detail fields such as shipment tracking, full
  status history, lifecycle timestamps, stored refund status, and the payment
  deadline after the initial checkout response.

For integration contracts and deployment acceptance requirements, see
[`FRONTEND_HANDOFF.md`](FRONTEND_HANDOFF.md) and
[`DEPLOYMENT_VPS.md`](DEPLOYMENT_VPS.md).
