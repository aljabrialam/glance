# Glance

*Your agent shops. You approve. Your stablecoins pay.*

Glance is a mobile app where an AI agent finds a product, gets the merchant's live
price (shipping and tax), checks it against **your** per-purchase limit, and pays
with a card backed by your USDC vault. Every charge is approved by you on the
payment provider's own page. Built at the Reap × 65labs Agentic Buildathon,
Singapore, 9 Oct 2026 — sandbox only, nothing is really bought or shipped.

Track: **Best Bridge Between Onchain and Real World** · Concept film:
`design/glance-product-film.html` · Clickable mockup: `design/glance-app-mockup.html`

## How it works

```
"Buy an Anker USB-C hub, under S$150"
   │  POST /api/intent            → { query, maxPriceCents }
   │  POST /api/search            → Reap products/search + details (SG, SGD), ≤3 results, agent's pick
   │  POST /api/quote             → Reap quotes (+ shipping option) → itemised cents + limit decision
   │  limit.evaluate(total, limit)  pure rule, inclusive, whole cents — blocks before any checkout
   │  POST /api/checkout          → Reap checkouts → hosted approval page (WebView)
   │  GET  /api/checkout/:id      → COMPLETED, orderId, finalAmount (what was actually charged)
   └─ Home shows vault balance, card last4, limit, this session's orders
```

- **Backend** `backend/` — FastAPI. Holds the Reap key, runs the agent, enforces the limit. Money is integer cents; floats are never used.
- **Mobile** `mobile/` — Expo (React Native). Talks only to the backend. Reap's hosted pages open in a WebView; `/done` returns the user via `glance://done`.
- **Vault** — Kwal (Payward) balance when configured; otherwise a clearly labelled mock.

## Run it

```bash
# backend
cp backend/.env.example .env            # fill REAP_API_KEY (team secret), leave the rest
cd backend && poetry install && poetry run pytest -q
poetry run uvicorn app.main:app --port 8000
cloudflared tunnel --url http://localhost:8000   # → set PUBLIC_URL in .env, restart

# enroll the test card once (human step on Reap's hosted page)
curl -X POST $PUBLIC_URL/api/enroll -H 'content-type: application/json' -d '{}' | jq .nextAction.url
curl $PUBLIC_URL/api/enrollment | jq .status     # wait for ACTIVE

# end-to-end by curl
PUBLIC_URL=$PUBLIC_URL scripts/happy_path.sh

# phone (Expo Go)
cd mobile && npm install && EXPO_PUBLIC_API_URL=$PUBLIC_URL npx expo start
```

## Rules we hold ourselves to

See `.specify/memory/constitution.md`. Highlights: user approves every charge on
the provider's page; card details never touch the app, server, logs or model;
limit is checked before any checkout; secrets live only in env vars; amounts shown
are what was actually charged.

## Spec-driven

`specs/001-agent-purchase/` — spec → clarify → **G1** → plan → **G2** → tasks →
implement → traceability → **G3**. Every acceptance criterion maps to a test whose
name carries its ID (`traceability.md`).
