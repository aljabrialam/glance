# Glance — backend API reference

The HTTP surface of the Glance API as implemented in `backend/app/main.py`, plus the
additions planned for the beta. The mobile app (`mobile/src/api.ts`) is the only intended
client. The short acceptance-criteria contract lives in
[`specs/001-agent-purchase/contracts/backend-api.md`](../specs/001-agent-purchase/contracts/backend-api.md).

Related: [architecture.md](architecture.md) §4 · [persistence.md](persistence.md) ·
[security.md](security.md)

## 1. Conventions

| Topic | Today | Beta |
|---|---|---|
| Base URL | `PUBLIC_URL` (an HTTPS tunnel) | `https://api.<domain>` per environment |
| Format | JSON in and out; `Content-Type: application/json` | unchanged |
| Money | Integer **cents**; every money field ends in `Cents`; one `currency` per session (`SGD`) | unchanged |
| Auth | None (single shopper) | `Authorization: Bearer <Supabase access token>` on every `/api/*` route except `/health`, `/done`, `/api/webhooks/*`; the user is `sub` |
| Request id | — | `X-Request-Id` accepted or generated, returned, logged |
| Versioning | Unversioned `/api/...` | Paths unchanged; changes are additive; the app sends `X-Glance-App: ios/1.2.0 (build)` so the API can refuse builds that are too old |
| CORS | `*` (demo convenience) | Restricted to the Expo web origin in `dev` only; native apps need none |
| Rate limits | — | WAF per-IP; per-user token bucket on `/api/intent`, `/api/search`, `/api/quote`, `/api/checkout` |

### Errors

FastAPI's shape, unchanged for the beta:

```json
{ "detail": "quote expired, re-quote" }
{ "detail": { "message": "total exceeds your per-purchase limit", "limitCents": 8000, "totalCents": 8446, "allowed": false, "overByCents": 446, "remainingCents": 0 } }
```

Reap failures are passed through verbatim so the app (and a judge) can see the real
request and response — never retried silently, never masked by a mock:

```json
{ "error": "reap", "request": { "method": "POST", "path": "/agentic/quotes", "body": { "...": "..." } }, "status": 400, "response": { "...": "..." } }
```

| Status | Meaning |
|---|---|
| `400` | Bad request (`variantId or quoteId+shippingOptionId required`, `limit must be positive`) |
| `401` | Beta: missing or invalid token |
| `403` | Checkout refused by the limit rule; `detail` carries the `LimitDecision` |
| `404` | No enrollment yet (`GET /api/enrollment`) |
| `409` | No `ACTIVE` enrollment configured for checkout |
| `410` | Quote expired; create a new quote |
| `422` | A photo was sent but no model can read it (`PhotoUnavailable`); also Pydantic validation errors |
| `502` | Reap returned ≥ 400; body is the `{error:"reap"}` object |

## 2. Endpoints (built)

### `GET /health`

```json
{ "ok": true, "enrollment": true, "reapKey": true }
```
Reports *presence* of the Reap key and an enrollment id, never their values. Used by the
ECS health check.

### `POST /api/enroll` — one-time card setup

Request `{ "email"?: string, "customerId"?: string }` (default `glance-demo-user`).
Calls `POST /agentic/enrollments` with `source: EXTERNAL`, `owner: { type: CLIENT_REFERENCE, id, email }`
and `presentation: { type: REDIRECT, returnUrl: "<PUBLIC_URL>/done?kind=enrollment" }`.
Returns Reap's enrollment object; the human opens `nextAction.url` and enters the card on
Reap's hosted page. The id is kept in state (or `REAP_ENROLLMENT_ID`).

Beta: `customerId` is always the authenticated user id; the response is reduced to
`{ enrollmentId, status, nextActionUrl, expiresAt }`.

### `GET /api/enrollment`

Reap's enrollment object; `status` must be `ACTIVE` before any checkout. `404` if none.

### `POST /api/intent`

```json
→ { "text": "Buy an Anker Nano USB-C hub, under S$150", "image": "<base64 JPEG or data: URL, optional>" }
← { "query": "Anker Nano USB-C hub", "maxPriceCents": 15000, "parser": "llm", "fromPhoto": false }
```
`parser` is `llm` or `regex`. With a photo and no model → `422`. The image is forwarded to
the model and discarded ([persistence.md](persistence.md) §2).

### `POST /api/search`

```json
→ { "query": "Anker Nano USB-C hub", "maxPriceCents": 15000 }
← { "searchId": "srch_…", "currency": "SGD", "pickId": "prd_01", "warnings": [],
    "products": [ { "id": "prd_01", "name": "Anker Nano USB-C Hub (8-in-1)", "merchant": null, "imageUrl": "…",
                    "priceCents": 7290, "variantId": "var_…", "requiresShipping": true, "available": true, "rank": 0 } ] }
```
Reap `products/search` (SG/SGD, `AVAILABLE_ONLY`, `price.max` from the ceiling, limit 10)
then `products/details` for `defaultVariant`. At most three products; `pickId` is the
cheapest within the ceiling; `rank 0` is the pick. `merchant` is `null` when the sandbox
returns its `"---"` placeholder, and the app shows "Merchant via Reap".

### `POST /api/quote`

Either a new quote or a re-price with a different delivery option:

```json
→ { "variantId": "var_…", "requiresShipping": true, "shippingOptionId"?: "ship_exp" }
→ { "quoteId": "qt_…", "shippingOptionId": "ship_exp" }
← { "quoteId": "qt_…", "itemCents": 7290, "shippingCents": 500, "taxCents": 656, "discountCents": 0, "totalCents": 8446,
    "currency": "SGD", "expiresAt": "2026-10-09T10:12:00Z",
    "shippingOptions": [ { "id": "ship_std", "name": "Standard delivery", "priceCents": 500, "selected": true } ],
    "limit": { "limitCents": 15000, "totalCents": 8446, "allowed": true, "overByCents": 0, "remainingCents": 6554 },
    "item": { "variantId": "var_…" } }
```
Reap `POST /agentic/quotes` (with `Idempotency-Key`, the session shipping address when
`requiresShipping`) or `POST /agentic/quotes/:id/shipping-option`. `limit` is
`limits.evaluate(totalCents, limitCents)` — the display-time check.

### `POST /api/checkout`

```json
→ { "quoteId": "qt_…", "item"?: { "name", "merchant", "imageUrl" }, "deliveryName"?: "Standard delivery" }
← { "checkoutId": "chk_…", "status": "REQUIRES_ACTION", "approvalUrl": "https://…reap…/…", "amountCents": 8446 }
```
Order of checks, each a hard stop: `409` no enrollment → re-read the quote from Reap →
`502` if it has no final amount → **`403` if `limits.evaluate` says blocked** → `410` if
`expiresAt` has passed → `POST /agentic/checkouts { quoteId, enrollmentId, presentation: REDIRECT /done?kind=checkout }`
(with `Idempotency-Key`, and `X-Simulate-Checkout` only where configured). The vault
balance before the spend is recorded with the checkout.

### `GET /api/checkout/{checkoutId}`

```json
← { "status": "COMPLETED", "terminal": true, "orderId": "ORD-SG-1003", "finalAmountCents": 8446, "currency": "SGD",
    "item": { "name": "…", "merchant": "…" }, "deliveryName": "Standard delivery",
    "vaultBeforeCents": 25000, "vaultAfterCents": 16554, "vaultSource": "kwal" }
```
Reads `GET /agentic/checkouts/:id`. On the first `COMPLETED` an order is recorded with
`finalAmount` — the only figure the Paid screen shows. The app polls this until `terminal`.
Beta: the row is updated by webhook/reconciliation and this endpoint reads the database
([persistence.md](persistence.md) §4); the shape is unchanged.

### `GET /api/home`

```json
← { "vaultBalanceCents": 25000, "vaultSource": "kwal", "vaultAddress": "0x…", "cardLast4": "4242", "currency": "SGD",
    "limitCents": 15000, "orders": [ { "checkoutId", "orderId", "finalAmountCents", "item", "deliveryName", "at" } ],
    "enrollmentActive": true }
```
`vaultSource` is `kwal` or `mock`; the app labels a mock balance explicitly. `cardLast4`
comes from the enrollment's `paymentMethod.last4` (cached 60 s) or `CARD_LAST4`.

### `PUT /api/limit`

`→ { "perPurchaseCents": 8000 }` · `← { "limitCents": 8000 }` · `400` if not positive. The
new limit applies to the next quote and to any checkout attempted afterwards.

### `GET /done?kind=checkout|enrollment`

HTML landing for Reap's `returnUrl`. It `postMessage`s `{ glance: 'done', kind }` to a
parent (web) and redirects to `glance://done?kind=…` (native). The app treats arrival as a
cue to read the checkout status, not as proof of payment.

## 3. Which Reap calls each endpoint makes

| Glance | Reap (`Authorization: Bearer`, `Reap-Version` on all) |
|---|---|
| `POST /api/enroll` | `POST /agentic/enrollments` (`Idempotency-Key`) |
| `GET /api/enrollment`, `GET /api/home` | `GET /agentic/enrollments/:id` |
| `POST /api/search` | `POST /agentic/products/search` → `POST /agentic/products/details` |
| `POST /api/quote` | `POST /agentic/quotes` (`Idempotency-Key`) · `POST /agentic/quotes/:id/shipping-option` |
| `POST /api/checkout` | `GET /agentic/quotes/:id` → `POST /agentic/checkouts` (`Idempotency-Key`, `X-Simulate-Checkout` in sandbox) |
| `GET /api/checkout/:id` | `GET /agentic/checkouts/:id` |

## 4. Planned additions (beta)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/webhooks/reap` | Signed event intake. Verify HMAC with the endpoint's signing secret and a timestamp window, store in `webhook_events` (unique `event_id`), apply the checkout/enrollment transition, `2xx` fast. Unverifiable → `401`, never processed |
| `GET` / `PUT` | `/api/address` | The shopper's shipping address (replaces the env-var address) |
| `GET` | `/api/enrollments` · `POST /api/enrollments/{id}/revoke` | List the user's stored cards; revoke one (final — a new enrollment is needed to re-add the card) |
| `GET` | `/api/orders?cursor=` | Paged order history beyond the 20 most recent returned by `/api/home` |
| `GET` | `/api/vault` | Vault status: `provisioning` / `ready` / `unavailable`, balance, address, top-up instructions |
| `DELETE` | `/api/account` | Account deletion: revoke enrollment, delete rows, confirm ([persistence.md](persistence.md) §6) |
| `GET` | `/api/config` | Minimum supported app build, feature flags (e.g. photo intent on/off) |

Mandates (`/agentic/mandates`) are not live at Reap; no Glance endpoint is planned until
they are.

## 5. Idempotency and retries

- **Today:** every Reap `POST` that requires an `Idempotency-Key` gets a fresh UUID. Safe
  because nothing retries; a network blip between us and Reap means the user re-taps and
  a second quote or checkout is created.
- **Beta:** the key is `checkouts.idempotency_key` / `quotes.id`, generated when the row
  is created and reused on retry. The Reap client retries idempotent calls on timeouts
  and `5xx` with jittered backoff (max 3). Non-idempotent reads are retried freely;
  `POST /agentic/checkouts` is retried **only** with the same key, so a user can never be
  charged twice for one tap.
- The app also sends `Idempotency-Key` on `POST /api/checkout` (a UUID per tap) so a
  flaky mobile network does not create two checkouts.

## 6. Example session (sandbox, curl)

`scripts/happy_path.sh` runs this end to end; it is also the nightly contract test.

```bash
PUBLIC_URL=https://api-staging.<domain>
curl -s $PUBLIC_URL/api/intent -d '{"text":"Buy an Anker Nano USB-C hub, under S$150"}' -H 'content-type: application/json'
curl -s $PUBLIC_URL/api/search -d '{"query":"Anker Nano USB-C hub","maxPriceCents":15000}' -H 'content-type: application/json'
curl -s $PUBLIC_URL/api/quote  -d '{"variantId":"var_…"}' -H 'content-type: application/json'
curl -s $PUBLIC_URL/api/checkout -d '{"quoteId":"qt_…"}' -H 'content-type: application/json'
curl -s $PUBLIC_URL/api/checkout/chk_…      # poll until "terminal": true
```
