# Implementation Plan: Agent Purchase, End to End

**Branch**: `001-agent-purchase` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-agent-purchase/spec.md`

## Summary

One happy-path purchase: sentence → search → quote → limit check → Reap hosted
approval → paid, in a React Native app backed by a FastAPI service that owns
the Reap key. Implementation base is the team's `glance.bundle` skeleton
(FastAPI + Expo, all endpoints and screens scaffolded, zero live Reap calls so
far). The plan adopts it, fixes two constitutional gaps (money as cents; the
limit rule as a pure, unit-tested function), switches the market to SG/SGD,
verifies every Reap call live by curl, and wires the phone demo.

## Technical Context

**Language/Version**: Python 3.10+ (backend); TypeScript 6 / React 19 / React Native 0.86 (mobile)

**Primary Dependencies**: FastAPI 0.115 (`fastapi[standard]`), httpx, Poetry; Expo SDK 57, `react-native-webview` 13.16, `@react-native-community/slider`, `expo-linking`

**Storage**: In-memory dict persisted to a JSON file (`STATE_FILE`, default `/tmp/glance-state.json`). No database (scope lock).

**Testing**: pytest for the pure limit/money rules and FastAPI endpoints (httpx `ASGITransport`, Reap mocked at the `call` boundary); `npx tsc --noEmit` for the app; `scripts/happy_path.sh` (curl) as the [e2e] check against the live sandbox.

**Target Platform**: Backend on any HTTPS host or a `cloudflared` tunnel; mobile via Expo Go on iOS/Android (WebView and Slider are bundled in Expo Go, so no dev build is needed); Expo web as a fallback.

**Project Type**: Mobile app + API service.

**Performance Goals**: Whole journey under 3 minutes on a phone (SC-001). Reap calls are the latency floor; nothing else is optimised.

**Constraints**: Sandbox only. Reap key only in backend env. HTTPS `PUBLIC_URL` required for Reap return URLs. Money in whole cents, no floats (constitution V). Code freeze 20:00 SGT.

**Scale/Scope**: One shopper, one session, 7 screens, 8 endpoints (+ `/api/enroll`, `/api/enrollment`, `/health`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status in bundle | Plan |
|---|---|---|
| I. User approves every charge | PASS — `POST /api/checkout` returns `nextAction.url`; app opens it in a WebView (`src/Approve.tsx`); `/done` returns to the app. | Keep. Observe the sandbox: `X-Simulate-Checkout: COMPLETED` may complete without a visible approval page; if so, document it in research.md and keep the hosted URL step in the UI. |
| II. Agent never touches card details | PASS — card entered only on Reap's hosted enrollment page; LLM sees only the sentence. | Keep. Add a log-hygiene check: `ReapError` logs request bodies, which never contain card data. |
| III. Limit before checkout | PARTIAL — `/api/checkout` returns 403 when over limit, but the rule is inline and float-based. | Extract `app/limits.py` (pure, cents) and call it from quote and checkout. |
| IV. Sandbox only, secrets in env | PASS — `.env` gitignored; `REAP_BASE_URL` defaults to sandbox. | Keep. Never print the key; `/health` only reports presence. |
| V. Honest amounts (whole cents) | **FAIL** — `money()` returns `float`; limit stored as `150.0`; `overBy` uses float subtraction. | Replace with `Decimal`-parsed integer cents everywhere in the backend (`amountCents` fields); app formats cents → `S$72.90`. Show `finalAmount` from `GET /agentic/checkouts/:id`, never the quote total. |
| VI. Specification first; AC IDs + tags | PASS — spec approved at G1; 15 ACs tagged. | Every test name includes its AC ID. |
| VII. Test pyramid; pure rules first | **FAIL** — no tests exist. | `tests/test_limits.py` (AC-001-07) written before any screen change; endpoint tests with Reap mocked; one [e2e] script. |
| VIII. Living documentation | PASS | Spec amended before any behaviour change. |
| IX. Stop and report | PASS | Report after each slice. |

**Gate result**: two violations (V, VII) are the first implementation slice; no
justification needed because both are fixed, not waived. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-purchase/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── backend-api.md   # Phase 1
├── gates/G1.md          # approved
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
backend/                     # from glance.bundle
├── app/
│   ├── __init__.py
│   ├── main.py              # endpoints; in-memory + JSON state
│   ├── reap.py              # Reap client: Bearer, Reap-Version, Idempotency-Key, ReapError(req/resp)
│   ├── intent.py            # sentence -> {query, maxPriceCents}; regex fallback, optional LLM
│   ├── vault.py             # Kwal balance via pws_client, else labelled mock
│   ├── money.py             # NEW: Decimal string/number -> int cents; format
│   └── limits.py            # NEW: pure evaluate(total_cents, limit_cents) -> LimitDecision
├── tests/
│   ├── test_limits.py       # AC-001-07 (pure)
│   ├── test_money.py        # cents parsing/formatting
│   └── test_api.py          # AC-001-01..05, 08, 10, 11, 13, 15 with Reap mocked
├── pyproject.toml           # + pytest, pytest-asyncio
└── .env.example

mobile/                      # from glance.bundle (Expo SDK 57)
├── App.tsx                  # 7 screens in one state machine (home/ask/results/quote/approve/paid/limit)
├── src/
│   ├── api.ts               # typed client; EXPO_PUBLIC_API_URL
│   ├── Approve.tsx          # WebView, detects /done or glance://
│   ├── Approve.web.tsx      # web popup + postMessage
│   └── theme.ts             # mockup colours/styles
├── app.json                 # scheme "glance"
└── package.json

scripts/
└── happy_path.sh            # AC-001-06 [e2e] by curl: search -> quote -> checkout -> status

design/                      # visual reference (unchanged)
docs/                        # context, scope lock, run sheet
```

**Structure Decision**: Mobile + API, two top-level projects as laid out by the
bundle (`backend/`, `mobile/`). The empty `frontend/` placeholder is removed in
favour of `mobile/`. Money and limit rules live in their own small modules so
they can be unit-tested without FastAPI.

## Implementation slices (ordered; each ends in a commit + 3-line report)

1. **Import bundle** into the repo (preserve its history via `git fetch` from the bundle, or copy files if history merge is noisy). Remove `frontend/`. Add `backend/.env.example`.
2. **Cents + pure limit rule** — `money.py`, `limits.py`, tests first (red), then wire into `main.py` (`*Cents` fields, `limitCents` default 15000, `PUT /api/limit` accepts `perPurchaseCents`). Update `api.ts` types and `App.tsx` formatters (`S$`, cents). `tsc` clean.
3. **SG market + Reap smoke** — env: `SHOP_COUNTRY=SG`, `SHOP_CURRENCY=SGD`, Singapore shipping address. Curl `products/search` for "Anker Nano USB-C Hub" with the real key; confirm `Reap-Version`; record the real response shapes in research.md. Fallback per scope lock if nothing returns.
4. **Enrollment** (human) — `POST /api/enroll` via tunnel, card on hosted page, poll to ACTIVE, set `REAP_ENROLLMENT_ID`. Read `paymentMethod.last4` for the home card.
5. **Happy path by curl** — `scripts/happy_path.sh` runs intent → search → quote → checkout → poll; prints `orderId` and `finalAmount`. Observe expired-quote and abandoned-approval behaviour; close the two spec markers.
6. **Phone demo** — Expo Go against the HTTPS backend; polish copy/states per mockup; decline/cancel toast; vault balance labelled "Mock balance (Kwal vault pending)" unless `vaultSource == "kwal"`.
7. **Converge + G3** — `/speckit-converge`, traceability table (AC → test or manual check), freeze.

## Complexity Tracking

No constitution violations are being waived; the two failures (V, VII) are
fixed in slice 2. No additional projects or patterns beyond the bundle's
structure.
