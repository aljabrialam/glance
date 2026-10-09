# Research: Agent Purchase, End to End

## R1. Implementation base

- **Decision**: Adopt `~/Downloads/glance.bundle` (team skeleton: FastAPI backend + Expo SDK 57 app).
- **Rationale**: Every endpoint in scope and all seven screens already exist, including WebView approval and the `/done` return page. It has never made a live Reap call, so verification — not scaffolding — is where the time goes.
- **Alternatives considered**: From scratch (slower, no benefit); mobile web app from the mockup HTML (rejected by the user: React Native is required).

## R2. Money representation

- **Decision**: Integer cents throughout the backend; parse Reap amounts with `Decimal(str(x))` then `int((d * 100).quantize(1))`; API fields named `*Cents`; the app formats `S$` + cents/100 with two decimals.
- **Rationale**: Constitution V forbids floats for money. The bundle's `money()` returns `float` and stores `limit: 150.0`.
- **Alternatives considered**: `Decimal` end-to-end over JSON (strings; heavier on the client); keep floats and round (violates the constitution).
- **Open**: Reap's exact amount shape (`{"amount": "72.90", "currency": "SGD"}` vs nested `amount.amount`). The bundle's `money()` handles both; `money.py` will too. Confirm in slice 3 against real responses.

## R3. Limit rule

- **Decision**: `limits.evaluate(total_cents: int, limit_cents: int) -> LimitDecision(allowed: bool, over_by_cents: int, remaining_cents: int)`. Inclusive: `total == limit` is allowed. Called from `/api/quote` (display) and `/api/checkout` (enforcement, 403 with `overByCents`).
- **Rationale**: Constitution III and VII; AC-001-07/08/09/10. Reap mandates are not live, so this is our code.

## R4. Market, product, identity

- **Decision**: `SHOP_COUNTRY=SG`, `SHOP_CURRENCY=SGD`. Demo product: Anker Nano USB-C Hub 8-in-1 (anker.com.sg, variant `52786047254813`, 72.90 SGD per the merchant sheet). Fixed demo buyer email and a Singapore shipping address from env. Default limit 15000 cents (S$150).
- **Rationale**: Team key is `sk_sg_sbx_*`; the event is in Singapore; the merchant sheet lists 10 SG merchants with electronics coverage. The mockup's Sony headphones are not in the sheet.
- **Fallback**: If SG search returns nothing by 17:45, switch to US/USD and any returned product (scope lock).

## R5. Reap request facts to confirm live (slice 3)

| Item | Expectation (docs) | Verify by |
|---|---|---|
| `Reap-Version` | `2025-02-14` accepted | first search call; if 4xx mentions version, use the value in the error |
| Search body | `{query, context{country,currency}, filters{price{max}, availability}}` | 200 with `products[]` incl. `previewVariant`/`priceRange` |
| Details | `{productIds}` → `products[].defaultVariant{id, price, requiresShipping}` | 200 |
| Quote | `{items[{variantId, quantity}], email, shippingAddress?}` + `Idempotency-Key` | `amountBreakdown.finalAmount`, `shippingOptions[]`, `expiresAt` |
| Shipping option | `POST /agentic/quotes/:id/shipping-option {shippingOptionId}` | re-priced quote |
| Checkout | `{quoteId, enrollmentId, presentation{REDIRECT, returnUrl}}` + `X-Simulate-Checkout: COMPLETED` | `status REQUIRES_ACTION`, `nextAction.url` |
| Poll | `GET /agentic/checkouts/:id` | terminal `COMPLETED` with `orderId`, `finalAmount` |
| Expired quote at checkout | unknown | create quote, wait past `expiresAt` (or use a stale id), attempt checkout; record status/body |
| Abandoned approval | unknown | create checkout without simulate header, never approve, poll; record whether it reaches a terminal state and when |

Each row is a curl in `scripts/happy_path.sh` or a one-off noted here with the real response.

## R6. Approval UX on device

- **Decision**: `react-native-webview` inside the app for the hosted page; detect `PUBLIC_URL/done` or `glance://done` and then poll `/api/checkout/:id`. On web, `Approve.web.tsx` opens a popup and listens for `postMessage`.
- **Rationale**: Constitution I (provider's own page); works in Expo Go without a dev build since WebView is bundled. The `/done` page both posts a message and deep-links `glance://`.
- **Risk**: With `X-Simulate-Checkout: COMPLETED`, the sandbox may complete immediately and `nextAction.url` may be a trivial page. Keep the step visible either way and show `finalAmount` from the poll.

## R7. Deployment / HTTPS

- **Decision**: `cloudflared tunnel --url http://localhost:8000` for the demo; `PUBLIC_URL` set to the tunnel URL; `EXPO_PUBLIC_API_URL` set to the same for the app. Fly/Railway only if the tunnel is unstable.
- **Rationale**: Fastest HTTPS; the bundle's `/done` page and `public_url()` already honour `PUBLIC_URL`.

## R8. Kwal vault

- **Decision**: Keep `vault.py` as is; show "Mock balance (Kwal vault pending)" whenever `vaultSource != "kwal"`. No Kwal work in this spec (scope lock).
