# Frontend Integration Handoff

This document is the implementation handoff for the Next.js App Router frontend.
The live OpenAPI contract remains authoritative at `GET /api/schema/`, with
Swagger UI at `GET /api/docs/`. This document records integration sequences and
security boundaries that are not usefully expressed by OpenAPI alone.

## Architecture boundary

```text
Browser -> Next.js UI/BFF -> Django API
                         -> public media storage or Django media route

Bale -> Django webhook directly
```

Next.js owns rendering, browser session cookies, server-side API calls, minimal
token refresh/proxy mechanics, and UI state. Django remains authoritative for
credentials and JWTs, permissions, catalog data, prices, inventory, carts,
checkout, orders, lifecycle transitions, refunds, payment verification, and
webhooks. The BFF must never reproduce a Django domain decision.

The intended browser topology is same-origin. Server-to-server requests from
Next.js to Django still use the existing JSON API and `Authorization: Bearer
<access-token>` contract.

## Current frontend implementation status

The executable Next.js implementation includes:

- a server-rendered storefront homepage with live category and latest-product
  discovery, catalog search, and independent empty/error/loading states;
- server-rendered catalog discovery and product detail;
- registration, login, logout, rotating JWT session cookies, customer-profile
  verification, profile editing, and address CRUD/default selection;
- guest and authenticated carts, including explicit replay-safe guest-cart
  merge during login;
- authenticated checkout and a result page for the newly created order;
- payment initiation, allowlisted generic URL handoff, Bale invoice handoff,
  generic return verification, and authoritative order-status refresh; and
- customer order history with item snapshots, pagination, owned order detail,
  and payment resumption for backend-eligible pending orders.
- approved product-review listing and aggregates, plus authenticated review
  submission, own-status display, and confirmed deletion on product detail.

JWTs and guest cart credentials are HttpOnly cookies. Personalized BFF
responses are private/no-store, state-changing BFF routes enforce exact-origin
checks, JSON-bearing routes validate content type and input, and Django remains
authoritative for every commerce decision. Login verifies `CustomerProfile`
before establishing cookies; an authenticated Django `User` whose profile is
missing is an explicit storefront error state, never a guest fallback.

The root Compose file falls back to `UnavailablePaymentGateway` unless a
provider is explicitly configured. There is no bundled browser payment
simulator. Bale testing requires its external Mini App/webhook environment; SDK
callback values remain informational.

The `/checkout/orders/{id}` page remains the immediate post-checkout result.
Account history and general owned detail live at `/account/orders` and
`/account/orders/{id}`.

## Storefront visual system

The current homepage and shared components are the visual source of truth for
Naghsh-e Jahan: a premium Persian RTL storefront for Isfahan handicrafts. The
root layout uses `lang="fa"`, `dir="rtl"`, and the bundled variable Vazirmatn
font. Shared CSS tokens define ivory backgrounds and surfaces, Persian
blue/lapis, turquoise, restrained gold accents, semantic success/destructive
colors, focus treatment, card shadows, and the optional `naghsh-pattern` motif.

Extend existing shared components and tokens instead of creating parallel page
styles. Interfaces should be mobile-first, remain usable at 360px and 390px,
and use natural Persian copy, visible keyboard focus, semantic landmarks, and
meaningful empty/loading/error states. Product imagery and all commercial facts
must come from Django; decorative copy must not imply unverified discounts,
ratings, availability, provenance, shipping promises, or delivery dates.

## Shared API conventions

- API routes are under `/api/v1/`. Schema and docs are `/api/schema/` and
  `/api/docs/`.
- Request and response bodies are JSON except for empty `204` responses.
- IRR values are whole-rial decimal strings, such as `"250000"`. Do not parse
  them through binary floating point or calculate authoritative totals in the
  frontend.
- Timestamps are ISO 8601 values. Treat server timestamps as authoritative.
- Authenticated endpoints require a SimpleJWT access token in the Bearer header.
- Ownership-scoped lookups deliberately return `404` for both unknown and
  another customer's objects.
- Validation errors are usually an object whose field values are arrays of
  messages. General failures commonly use `{"detail": "..."}`. SimpleJWT may
  also include token error codes. Do not assume one universal error envelope.
- Throttled requests return `429`. Do not retry immediately; honor
  `Retry-After` when present and show a bounded retry state.
- Product and order collections use
  `{"count", "next", "previous", "results"}` page-number pagination.
  Category and address lists are unpaginated. Product and order `page_size` is
  capped at 100. `next` and `previous` are request-origin URLs; when Django is
  reached through an internal hostname, use their page parameters rather than
  exposing that internal origin to the browser.

## Public catalog

All catalog operations are unauthenticated and read-only.

- `GET /api/v1/categories/` returns all active categories as a flat list. Each
  row has `id`, `name`, `slug`, and an optional active `parent` summary. Build a
  navigation tree client-side if needed; there is no nested children endpoint.
- `GET /api/v1/categories/{slug}/` returns one active category.
- `GET /api/v1/products/` returns the lightweight product list with current
  `price`, `in_stock`, category summary, optional `primary_image`, and approved
  review aggregates. `average_rating` is a one-decimal string or `null`, and
  `review_count` is zero or greater. Pending and rejected reviews are excluded.
- `GET /api/v1/products/{slug}/` adds `description` and ordered `images`.

Supported product query parameters are:

- `category`: exact category slug
- `min_price`, `max_price`: whole-rial values
- `in_stock`: boolean
- `search`: name and description search
- `ordering`: `price`, `-price`, `created_at`, or `-created_at`
- `page`, `page_size`

List prices and stock indicators are current views, not checkout guarantees.
Product-list fetches are `no-store` because their card-rating aggregates change
with moderation and review deletion; categories and product details retain the
existing bounded server cache. Checkout still revalidates product availability
and recomputes all prices and totals.

Image fields are URL strings generated by Django storage with `alt_text`,
`is_primary`, and `position`. See the media deployment boundary below before
configuring Next.js image optimization.

## Product reviews and moderation

Product review APIs use the active product slug and keep the homepage's static
testimonial carousel entirely separate:

- `GET /api/v1/products/{slug}/reviews/` returns a page-number-paginated list of
  approved reviews. Rows contain `id`, integer `rating`, `comment`, public
  `author_name`, `created_at`, and nullable `store_reply`. A reply contains only
  `comment`, `created_at`, and `updated_at`; status and private customer data are
  absent.
- `GET /api/v1/products/{slug}/reviews/aggregate/` returns
  `average_rating` as a one-decimal string and `review_count`, using approved
  reviews only. The empty representation is
  `{"average_rating": null, "review_count": 0}`.
- `GET /api/v1/products/{slug}/reviews/mine/` returns the authenticated
  customer's review including `status`, or `404` when none exists.
- `POST /api/v1/products/{slug}/reviews/mine/` accepts only integer `rating`
  from 1 through 5 and a non-blank `comment`, creates `PENDING`, and returns
  `201`. Author, product, status, identifiers, and timestamps are not writable.
  A duplicate returns `409`.
- `DELETE /api/v1/products/{slug}/reviews/mine/` deletes the current customer's
  review and returns `204`. `PUT` and `PATCH` are unavailable; a different
  review requires deletion followed by a fresh pending submission.

Anonymous callers can use public list/aggregate endpoints but receive `401` on
the personal endpoint. Unknown, inactive, or category-hidden products return
`404`. Authenticated users without `CustomerProfile` fail safely. One existing
review per product/customer is enforced by a database unique constraint, while
POST and DELETE share the `review_mutation` throttle so deletion/resubmission
cycles are also limited.

Django Admin exposes read-only review records and explicit approve/reject
actions for pending reviews. Moderation requires the `change_productreview`
permission; `is_staff` alone is insufficient. Approved and rejected reviews are
not transitioned again by these actions. `ProductReviewReply` is managed as a
separate Admin model; its one-to-one review relation enforces at most one reply.
Add/change/delete operations use their corresponding Django model permissions.

The authenticated operator API is intentionally separate from customer review
operations:

- `GET /api/v1/management/reviews/` requires a staff account plus either
  `view_productreview` or `change_productreview`. It supports `status`,
  `has_reply`, `search`, `page`, and `page_size`.
- `POST /api/v1/management/reviews/{id}/moderate/` accepts only `APPROVED` or
  `REJECTED`, requires `change_productreview`, and only transitions `PENDING`.
- `POST`, `PATCH`, and `DELETE`
  `/api/v1/management/reviews/{id}/reply/` require review visibility plus the
  matching add/change/delete `ProductReviewReply` permission.

Mutation paths lock the review row and rely on the one-to-one database
constraint for concurrent reply creation. Staff status by itself grants no API
access.

The Next.js product page server-renders the bounded public list and aggregate.
Its client component calls the same-origin
`/api/products/{slug}/reviews/mine` BFF route for personal GET/POST/DELETE.
Personal responses are private/no-store, mutations use exact-origin protection,
JWT refresh stays server-side, and backend validation, duplicate, and throttle
responses remain authoritative.

The operations dashboard lives at `/dashboard`, with order operations at
`/dashboard/orders` and review moderation at `/dashboard/reviews`. The legacy
`/management/reviews` route redirects to the review dashboard. Its Django APIs
remain under `/api/v1/management/`, and its same-origin BFF routes remain under
`/api/management/`; UI and API namespaces are intentionally separate.

Order dashboard endpoints require active staff plus explicit Django model
permissions. Viewing summary/list/detail requires `orders.view_order` or
`orders.change_order`; lifecycle and refund commands require
`orders.change_order`; shipment editing independently requires
`orders.change_shipment`. Commands call the existing locked domain services and
never write status directly. Summary revenue counts each order with at least one
successful payment once, pending fulfillment covers paid, processing, and
shipped orders, and low stock means an active product with physical stock of
five or fewer.

The dashboard uses separate `management_access` and `management_refresh`
HttpOnly cookies so an operator session does not become a storefront customer
session. Its `/api/management/...` BFF routes validate input, enforce
exact-origin protection for mutations, refresh tokens server-side, and return
`private, no-store` responses. Django remains authoritative for all permissions,
order transitions, refund resolution, shipment rules, moderation transitions,
and reply uniqueness.

## Authentication and account

### Django contract

- `POST /api/v1/auth/register/` accepts `email`, `password`, `first_name`,
  `last_name`, and `phone_number`; it creates the account but does not log in.
- `POST /api/v1/auth/login/` accepts `email` and `password`, returning `access`
  and `refresh`.
- Access tokens live for 5 minutes. Refresh tokens live for 7 days.
- `POST /api/v1/auth/token/refresh/` accepts `refresh`, rotates it, blacklists
  the submitted refresh token, and returns a new `access` and `refresh`.
- `POST /api/v1/auth/logout/` accepts `refresh`, blacklists it, and returns
  `204`. It intentionally does not require a still-valid access token and does
  not revoke an already-issued access token.
- `GET /api/v1/account/profile/` returns the current customer profile.
- `PATCH /api/v1/account/profile/` updates `first_name`, `last_name`, and
  `phone_number`; email and privilege fields are not writable.

### Next.js BFF contract

The browser must not receive tokens in JavaScript-readable storage. The BFF
should call Django login/refresh/logout server-side and keep access and refresh
tokens in `Secure`, `HttpOnly`, appropriately scoped cookies. Because cookies
are ambient browser credentials, the BFF must enforce its own CSRF/origin
protection on state-changing browser routes; Django's Bearer-token API does not
provide that BFF boundary.

Refresh rotation is single-use. Concurrent server renders or route handlers
must not independently refresh the same token: coalesce/serialize refresh for a
browser session and replace both cookies atomically after success. Only a JWT
refresh endpoint `401` definitively rejects credentials and clears that session's
cookies. Refresh `429` preserves cookies and returns `429`, forwarding only a
valid seconds/canonical HTTP-date `Retry-After`. Refresh `5xx`, unexpected statuses,
malformed success bodies, network failures, and the 10-second refresh timeout
preserve cookies and return a safe `503`. No protected operation resumes without
verified replacement tokens. The customer page proxy stops rendering on these
temporary failures instead of rendering the user as a guest; management and
customer BFF routes share this classification but retain separate cookies.

No failed refresh is automatically retried within a request. Existing in-process
coordination shares pending results and retains completed results for five seconds,
including failures. A lost response can mean the old refresh token was already
blacklisted: preserving its cookie cannot recover the missing replacement. A later
independent request may receive `401` and require login. The BFF neither assumes
rotation succeeded nor replays the protected operation after an ambiguous failure.
Coordination remains local to one process; multiple workers need shared refresh
coordination before deployment. On logout, submit the stored refresh token to
Django, then clear both cookies even if the remote token is already invalid.

Registration should redirect to login or invoke the login flow explicitly; a
successful registration response contains no JWTs.

## Addresses

- `GET|POST /api/v1/account/addresses/` lists or creates owned addresses.
- `GET|PATCH|DELETE /api/v1/account/addresses/{id}/` operates only on an owned
  address.
- `POST /api/v1/account/addresses/{id}/set-default/` selects the default.
- Required shipping fields are recipient first/last name, E.164 phone number,
  province, city, address, and ten-digit Iranian postal code. `title` is
  optional.
- Ownership and `is_default` are never client-writable. The first address made
  through the API becomes default. Deleting the default does not promote
  another address, so zero defaults is valid.

## Cart and guest identity

`GET /api/v1/cart/` without credentials returns an empty representation and
does not create a database row. The first successful guest
`POST /api/v1/cart/items/` creates a cart and returns its opaque UUID credential
in the `X-Cart-Token` response header. Later guest cart calls send the same
header.

The BFF should store that token in a separate `Secure`, `HttpOnly`, same-site
browser cookie, capture updated response headers from Django, and inject
`X-Cart-Token` only on server-to-server guest cart requests. Treat it as a
bearer credential; do not put it in URLs, localStorage, analytics, or logs.

- `POST /api/v1/cart/items/` accepts `product_slug` and positive `quantity`.
- `PATCH /api/v1/cart/items/{id}/` accepts the new positive `quantity`.
- `DELETE /api/v1/cart/items/{id}/` removes the item and returns `204`.
- Authenticated cart requests use the customer cart and ignore
  `X-Cart-Token`.
- After login, call `POST /api/v1/cart/merge/` with the Bearer access token and
  guest `X-Cart-Token`. Clear the guest cookie only after a successful merge
  (or after deliberately handling a stale/unknown token). A successful merge
  consumes the guest credential and cannot be replayed.

Cart responses are private/no-store and include current product prices,
subtotal, availability flags, and availability reasons. A cart does not reserve
or decrement stock. Merge can preserve quantities that now exceed stock; the UI
must display `is_available`/`availability_reason` and let checkout remain the
authority.

## Checkout and orders

`POST /api/v1/checkout/` requires authentication and an active non-empty cart.
It accepts optional `address_id`; omission selects the current default address.
The response is a newly created `PENDING_PAYMENT` order with immutable product,
price, total, and shipping-address snapshots plus `payment_expires_at`.

Checkout converts the cart and creates 15-minute inventory reservations, but it
does not decrement physical stock. Django revalidates current products, prices,
stock, address ownership, and competing reservations. The UI must discard any
locally calculated total in favor of the response.

- `GET /api/v1/orders/` returns the customer's newest-first paginated orders,
  including immutable item snapshots used for the history summary.
- `GET /api/v1/orders/{id}/` returns owned order totals, item snapshots,
  shipping snapshot, status, and creation/update timestamps.
- `POST /api/v1/orders/{id}/cancel/` takes no body and returns `id`, `status`,
  `refund_status`, and `cancelled_at`. It is available only for states the
  backend allows and returns `409` for a rejected transition.

Order status values are `PENDING_PAYMENT`, `PAID`, `PROCESSING`, `SHIPPED`,
`DELIVERED`, `CANCELLED`, and `EXPIRED`. The frontend must render these values;
it must not infer or trigger lifecycle transitions other than the exposed
customer cancellation command.

## Payments and Bale

1. Call `POST /api/v1/orders/{order_id}/payments/` with `{}`. Django copies the
   authoritative order amount/currency and returns a payment attempt. The first
   call normally returns `201`; replay while the attempt is pending returns the
   same attempt with `200` and does not create a second gateway charge.
2. A generic gateway may return `payment_url`. Bale returns
   `payment_identifier` and `payment_url` is null. The identifier is the opaque
   value passed unchanged to `Bale.WebApp.openInvoice(...)`; it is available
   only while the attempt is `PENDING`.
3. The Bale Mini App callback status is UX-only. It is not proof of payment.
   Bale success reaches Django directly through the webhook, and Django performs
   an authoritative provider inquiry before finalizing the order.
4. After the Bale UI closes/returns, query the owned order and treat its Django
   `status` as truth. A short bounded poll may be used while the order remains
   `PENDING_PAYMENT`; do not synthesize `PAID` from query parameters or SDK
   callback data.

`POST /api/v1/orders/{order_id}/payments/{payment_id}/verify/` is the generic
gateway return-verification contract. It accepts
`{"callback_data": { ...untrusted provider return fields... }}` and delegates
verification to the configured gateway. It is not the Bale success path: the
current Bale adapter intentionally does not accept client-event verification.

Attempts expose only `id`, `status`, amount, currency, optional customer
handoff fields, and timestamps. Internal gateway references, provider
transaction IDs, credentials, and idempotency keys are never frontend data.
Retries must use the initiation endpoint again; the backend decides whether to
return the existing pending attempt or create a new attempt. Webhook routes are
Django/provider-only and must never be proxied as browser BFF operations.

## Caching, CORS, and media deployment boundaries

With the target same-origin BFF topology, browser requests go to Next.js and
server-to-server calls are not governed by browser CORS. Django CORS credentials
remain disabled; do not forward browser cookies to Django. If a future design
allows direct cross-origin browser calls, it is a separate contract change,
especially because guest token response headers would need deliberate exposure.

Cart/account/order/payment and personal-review responses must not be
shared-cached. Public catalog and approved-review rendering may use Next.js
caching with deliberate revalidation, while cart and checkout always rely on
fresh Django responses.

Product image URLs are generated from Django's request/storage context. In
production, the media storage or reverse proxy must expose those URLs to the
browser. If Next.js calls Django through an internal hostname, the deployment
must still produce a public media origin (for example through the selected
storage backend or correctly forwarded public host/scheme), or the BFF must map
the returned media path to the public same-origin route. Configure Next.js
image allowlisting only after that public media origin is selected.

Application throttles currently use local-memory cache and are suitable for the
default single-worker/single-replica assumption. Scale-out requires a shared
Django cache or equivalent trusted ingress limits before treating configured
rates as globally enforced.

## Integration responsibility classification

### A — backend blockers

None found for the implemented catalog, account, cart, checkout, order, payment,
and product-review flows.

### B — Next.js/BFF responsibility

- Keep JWTs and the guest cart credential out of localStorage and
  JavaScript-readable cookies.
- Preserve CSRF/origin protection on cookie-authenticated BFF mutations.
- Serialize rotating refresh-token use and update cookies atomically.
- Forward the Bearer token and, for guest cart calls, `X-Cart-Token`. The
  production BFF also carries the ingress-written, validated
  `X-Naghsh-Client-IP` only to the Docker-internal Caddy listener so Django can
  enforce per-client anonymous throttles; browser-provided forwarding headers
  are never trusted.
- Merge the guest cart explicitly after login and clear its cookie only after
  the merge outcome is handled.
- Treat all client payment return data as untrusted and poll Django order state
  after Bale closes.
- Preserve structured API errors and `429` retry behavior instead of converting
  every failure to a generic `500`.
- Mark personalized BFF responses private/no-store; only public catalog data is
  eligible for shared or Next.js server caching.

### C — deployment/provider responsibility

- Route the browser-facing site and BFF as same-origin, while keeping direct
  Django webhook and health routes reachable where required.
- The current Bale handoff requires a Bale Mini App client capable of calling
  `Bale.WebApp.openInvoice(...)`; Django does not return a guaranteed standalone
  browser checkout URL. If payments must launch outside Bale, treat that as a
  new provider/product requirement rather than deriving a URL from the opaque
  identifier.
- Select durable shared media storage or a persistent media route and ensure
  serialized image URLs use a public origin.
- Configure trusted proxy/host/origin settings and TLS according to the
  production deployment contract in `README.md`.
- Add a shared throttle cache or ingress enforcement before multiple workers or
  replicas are used.

### D — deferred nice-to-haves

- Customer order detail currently exposes the current status but not shipment
  carrier/tracking data, status-history rows, lifecycle timestamps, the stored
  refund status, or the checkout reservation deadline after the initial
  checkout response. Add fields only when a concrete UI requirement selects
  them.
- OpenAPI documents the usable endpoint and data contract but does not normalize
  every error shape, and its known `status` enum naming collision remains. A
  generated client/error abstraction can be evaluated after the first frontend
  integration proves it useful.
- Category children can be derived from the complete category list; a dedicated
  nested-tree endpoint is not currently justified.

These D items must not be implemented merely to make the API more stylistically
uniform.
