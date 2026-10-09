# Contract: Glance backend API

Base: `PUBLIC_URL` (HTTPS). JSON in/out. Money = integer cents. Errors from
Reap are surfaced verbatim as `502 {error:"reap", request, status, response}`
(AC-001-15); never retried silently.

| Method | Path | Request | Response | ACs |
|---|---|---|---|---|
| GET | `/health` | — | `{ok, enrollment: bool, reapKey: bool}` | — |
| POST | `/api/enroll` | `{email?, customerId?}` | Reap enrollment incl. `nextAction.url` (hosted card page) | setup |
| GET | `/api/enrollment` | — | Reap enrollment; `status` must be `ACTIVE` | setup |
| POST | `/api/intent` | `{text}` | `{query, maxPriceCents}` | 01 |
| POST | `/api/search` | `{query, maxPriceCents?}` | `{products[≤3], pickId, warnings[]}` | 02 |
| POST | `/api/quote` | `{variantId, requiresShipping?}` or `{quoteId, shippingOptionId}` | Quote (see data-model) incl. `limit: LimitDecision` | 03, 11 |
| POST | `/api/checkout` | `{quoteId, item?}` | `{checkoutId, status, approvalUrl}`; `403 {overByCents}` if over limit; `409` no enrollment; `410` expired | 04, 08 |
| GET | `/api/checkout/{id}` | — | `{status, terminal, orderId, finalAmountCents, item, vaultBeforeCents, vaultAfterCents, vaultSource}` | 05 |
| GET | `/api/home` | — | Home (see data-model) | 13 |
| PUT | `/api/limit` | `{perPurchaseCents}` | `{limitCents}` | 10 |
| GET | `/done?kind=checkout\|enrollment` | — | HTML: `postMessage({glance:'done'})` + deep-link `glance://done` | 06, 12 |

## Reap calls made (sandbox)
`POST /agentic/products/search` → `POST /agentic/products/details` →
`POST /agentic/quotes` (Idempotency-Key) → `POST /agentic/quotes/:id/shipping-option` →
`POST /agentic/checkouts` (Idempotency-Key, `X-Simulate-Checkout`) → `GET /agentic/checkouts/:id`.
Headers on every call: `Authorization: Bearer`, `Reap-Version`.

## Mobile client (`mobile/src/api.ts`)
Same shapes, typed. `EXPO_PUBLIC_API_URL` = `PUBLIC_URL`. Approval opens
`approvalUrl` in a WebView and treats navigation to `${API_URL}/done` or
`glance://done` as "returned"; then polls `GET /api/checkout/{id}` until `terminal`.
