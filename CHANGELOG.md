# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0]

These notes describe the v1.0.0 source-release candidate and its implemented
scope. The application has been validated locally; final-revision hosted CI
and public production deployment are not claimed.

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
  runtime/development audits to CI. Runtime npm audits fail on any severity;
  full npm audits fail on High or Critical findings, with strict audits for
  both Python locks.
- Upgraded Next.js and `eslint-config-next` from `16.3.8` to `16.4.3` to address
  newly published runtime advisories, and resolved development-only Zod from
  `4.6.5` to `4.6.7`. Local audits passed for the verified implementation
  baseline described below.
- Removed the temporary CI exception for `GHSA-vfj7-8cjw-p6xm` after the
  advisory was withdrawn and disappeared from npm audit results. CI now fails
  directly on any High or Critical npm advisory and retains the all-severity
  production runtime audit.

### Fixed

- Prevented stale product Admin changelist saves from overwriting concurrent
  inventory deductions or restoration while retaining status management.
- Made authorized management status retries replay-safe using locked order state
  and the latest actor-specific history, without repeating side effects.
- Preserved management login rate limits and safe temporary-service errors
  instead of reporting them as invalid credentials.
- Preserved session cookies on transient or ambiguous refresh failures, stopped
  protected operations without verified tokens, and retained definitive rejection
  handling and refresh coordination.
- Removed nested main landmarks from customer order pages.
- Allowed the non-root frontend development user to write TypeScript build info.

### Validation

- Local release verification of implementation commit
  `921cedd7950ab256322413b6933325110f2a7046` passed the complete PostgreSQL-backed
  backend suite, frontend unit/BFF integration suites, Ruff, ESLint, TypeScript,
  Django system/deployment checks, migration consistency and OpenAPI validation.
- Clean npm installation, Python lock validation and pip checks, both strict
  Python dependency audits, and the explicit runtime/full npm security gates
  passed locally. Production application images built and isolated liveness/
  readiness smoke checks passed. These are local results, not hosted CI results.
- GitHub Actions repeats the release gates on pushes to `main` and pull requests
  targeting `main`. A successful run for the final release revision remains
  unverified and is still required before publishing the source release.
- Earlier local browser QA covered 360, 390, 768 and 1440 px without a confirmed
  P0 or P1 finding. Mobile filter backward focus wrapping and mobile-menu focus
  restoration after Escape remain known accessibility follow-ups. No exhaustive
  WCAG, assistive-technology or cross-browser certification is claimed.

### Not yet production-verified

- The platform has not been publicly deployed. Public DNS, TLS operation,
  external monitoring, and a provider-specific off-server backup and restore
  drill remain deployment acceptance work.
- Live Bale payment success, provider inquiry, webhook delivery/replay, and the
  full Mini App return flow have not been verified against the real provider.
  No real payment is claimed to have been completed.
- The production Compose stack configures a persistent single-host media
  volume. Backup durability, real production secrets and capacity sizing still
  require acceptance in the selected hosting environment.

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
