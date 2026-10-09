# Glance — handoff context

Hackathon: Reap x 65labs Agentic Buildathon, Singapore, Fri 9 Oct 2026. Submit by 9:00 pm SGT (aim for 8:45).
Target track: "Best Bridge Between Onchain and Real World" (fallback: "Most Worthwhile Problem" if Kwal isn't ready).
Judging uses the submission and demo video, so one polished happy path matters more than more features.

## What Glance is
A mobile app where an AI agent finds a product, gets a live quote (shipping and tax), checks it against the user's
per-purchase limit, and pays with a card backed by the user's USDC vault (Kwal). The user approves every
charge on Reap's hosted approval page. Reap checkout is sandbox: nothing is really bought or shipped.

## Rules (from the brief)
- The Reap API key lives only in backend env vars. The mobile app talks only to the backend.
- Don't scrape merchant checkout pages. Never pass card details to an LLM. No travel, gambling, or adult content.
- The spending limit is enforced in app logic (Reap mandates aren't available).
- Use Reap's hosted enrollment and approval pages; don't rebuild them.
- If a Reap call fails, show the exact request and response; don't silently mock it.
- Never claim the Kwal vault is live when it isn't. Until it is, the UI shows "Mock balance (Kwal vault pending)".
- Kwal registration is NOT idempotent: run `register` once only and keep the credentials outside any git checkout.

## Repo layout
```
backend/   FastAPI (Poetry). Entry point: app/main.py -> `app`
  app/main.py    endpoints + in-memory/JSON state (limit, orders, enrollment)
  app/reap.py    Reap client (Bearer, Reap-Version, Idempotency-Key; ReapError carries the exact req/resp)
  app/intent.py  text -> {query, maxPrice}; regex fallback, optional OpenAI/Anthropic via LLM_API_KEY
  app/vault.py   Kwal balance via the kwal skill's pws_client (KWAL_SCRIPTS); otherwise a labelled mock of $250
mobile/    Expo (SDK 57) React Native + web
  App.tsx              screens: home, ask, results, quote, approve, paid, limit
  src/api.ts           typed backend client (EXPO_PUBLIC_API_URL, default http://localhost:8000)
  src/Approve.tsx      native: Reap hosted page in a WebView, detects the /done redirect
  src/Approve.web.tsx  web: opens a popup, listens for postMessage from /done
  src/theme.ts         colors and styles matching the mockup
```

## Backend endpoints
- GET  /health -> {ok, enrollment, reapKey}
- POST /api/enroll -> creates a Reap enrollment (source EXTERNAL, owner CLIENT_REFERENCE) and returns the hosted URL where the user adds the test card
- GET  /api/enrollment -> enrollment status (must be ACTIVE before any charge)
- POST /api/intent {text} -> {query, maxPrice}
- POST /api/search {query, maxPrice} -> up to 3 products plus pickId (cheapest under the ceiling); calls Reap search, then details
- POST /api/quote {variantId, shippingOptionId?} -> quote + overLimit/overBy
- POST /api/checkout {quoteId} -> {checkoutId, approvalUrl}; returns 403 if over the limit, checks quote expiry
- GET  /api/checkout/{id} -> {status, orderId, finalAmount, vaultBefore/After}
- GET  /api/home -> {vaultBalance, vaultSource, cardLast4, limit, orders}
- PUT  /api/limit {perPurchase}  (default 150)
- GET  /done -> return page: posts a message back to the web popup and deep-links glance://done

Reap flow: products/search -> products/details -> quotes -> (quotes/:id/shipping-option) -> checkouts -> poll GET checkouts/:id.
Sandbox base URL: https://sandbox.api.reap.global. The sandbox sends `X-Simulate-Checkout: COMPLETED` by default (REAP_SIMULATE_CHECKOUT).

## Env vars (backend/.env, gitignored)
REAP_API_KEY, REAP_VERSION (docs use 2025-02-14; not confirmed for our key), REAP_BASE_URL, REAP_ENROLLMENT_ID,
PUBLIC_URL (public https URL of the backend, used for the /done return URL), APP_SCHEME (glance),
LLM_API_KEY / LLM_MODEL (optional), KWAL_SCRIPTS (path to kwal-skill/skills/agent-payment/scripts),
MOCK_VAULT_BALANCE, BUYER_EMAIL, SHIP_FIRST_NAME/LAST_NAME/PHONE/CITY/STATE/POSTAL/COUNTRY, SHOP_COUNTRY, SHOP_CURRENCY, STATE_FILE

## Run locally
```
cd backend && poetry install && poetry run fastapi dev app/main.py --port 8000
cd mobile && npm install && EXPO_PUBLIC_API_URL=https://<public-backend> npx expo start   # use --web for the browser
```
For a public HTTPS URL (Reap needs one for the return URL): `cloudflared tunnel --url http://localhost:8000`, then set PUBLIC_URL to the tunnel URL.

## Status
Done and checked locally:
- The backend imports and serves /health, /api/intent and /api/home. A clean `poetry install` + `fastapi run` works.
- The Expo app type-checks (`npx tsc --noEmit`) and the Home screen renders in Expo web with the mock vault.
- The Kwal balance code is written but untested (no Kwal credentials yet).

NOT done / blocked:
- No Reap key yet, so no live Reap call has run (enroll, search, quote, checkout all unverified).
- No enrollment yet. Steps: POST /api/enroll, the user enters the test card on Reap's hosted page, wait for ACTIVE, then set REAP_ENROLLMENT_ID.
- Kwal: need the owner EVM wallet address (Ink Sepolia, chain 763373, funded with test ETH and test USDC). Then, from the kwal skill:
  `python3 scripts/register.py check`, `register` (ONCE), `setup`, `status`, `funding`.
- Devin's Fly.io deploy tool failed to detect the project, even for a minimal FastAPI app (likely a tool problem). Deploy anywhere that runs
  `fastapi run app/main.py` from backend/ (Fly, Railway, Render), or use the tunnel.
- No git remote or PR yet. End-to-end demo flow and demo video still to do.

## Next steps (in order)
1. Add REAP_API_KEY and REAP_VERSION to backend/.env. Curl each Reap call before trying it from the UI.
2. Get a stable public backend URL and set PUBLIC_URL.
3. Enroll and add the test card, wait for ACTIVE, set REAP_ENROLLMENT_ID.
4. Run search -> quote -> checkout -> approve -> paid end to end in the app.
5. Set up Kwal (register once), set KWAL_SCRIPTS, and confirm /api/home shows vaultSource "kwal".
6. Polish the happy path, record the demo video, submit.
