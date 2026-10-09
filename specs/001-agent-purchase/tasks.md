# Tasks: Agent Purchase, End to End

**Input**: `specs/001-agent-purchase/` (spec, plan, research, data-model, contracts, quickstart)

**Tests**: Required by constitution VI/VII. Pure rules first; test names contain AC IDs.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (slice 1)

- [x] T001 Import `~/Downloads/glance.bundle` (`backend/`, `mobile/`, `HANDOFF.md` → `docs/handoff-bundle.md`) into the repo; remove `frontend/`; keep `.gitignore` union
- [x] T002 Add `backend/.env.example` (SG defaults, no values) and point `backend/.env` at the root `.env` values (REAP_*, PUBLIC_URL, SHOP_COUNTRY=SG, SHOP_CURRENCY=SGD, SHIP_* Singapore, BUYER_EMAIL)
- [x] T003 Add pytest + pytest-asyncio to `backend/pyproject.toml`; `poetry install`; `npm install` in `mobile/`; `npx tsc --noEmit` baseline

## Phase 2: Foundational — cents + pure limit rule (slice 2) ⚠️ blocks all stories

- [x] T004 [P] `backend/tests/test_limits.py`: AC-001-07 cases (under, equal→allowed, over→over_by, zero/negative guards) — RED
- [x] T005 [P] `backend/tests/test_money.py`: parse `"72.90"`, `72.9`, `{"amount":"72.90","currency":"SGD"}`, nested `amount.amount`, reject NaN/strings; format cents → `72.90` — RED
- [x] T006 `backend/app/limits.py`: `LimitDecision` dataclass + `evaluate(total_cents, limit_cents)` — GREEN T004
- [x] T007 `backend/app/money.py`: `to_cents(x) -> int | None` via `Decimal`, `fmt(cents)` — GREEN T005
- [x] T008 `backend/app/main.py`: replace `money()` with `to_cents`; state `limitCents` (default 15000) with migration from old `limit`; `_quote_out` returns `*Cents` + `limit: LimitDecision`; `/api/checkout` enforces via `limits.evaluate` (403 `{overByCents}`); `/api/checkout/{id}` returns `finalAmountCents`; `/api/home` returns `limitCents`, `vaultBalanceCents`; `PUT /api/limit {perPurchaseCents}`
- [x] T009 `backend/app/intent.py`: return `maxPriceCents`; prompt says SGD; regex accepts `S$`/`$`
- [x] T010 `backend/app/vault.py`: return `balanceCents` (int) from minor units; mock from `MOCK_VAULT_BALANCE_CENTS=25000`
- [x] T011 `mobile/src/api.ts`: types to `*Cents`, `limit: LimitDecision`, `perPurchaseCents`; `mobile/App.tsx`: `money(cents, currency)` → `S$72.90`, limit slider in cents (S$50–S$300 step S$10), default ask text "Buy an Anker Nano USB-C hub, under S$150"; `npx tsc --noEmit` clean

**Checkpoint**: `poetry run pytest -q` green; app type-checks; commit "slice 2".

## Phase 3: US1 — Happy path purchase (P1) 🎯

- [x] T012 [P] [US1] `backend/tests/test_api.py` with Reap `call` monkeypatched: AC-001-01 intent → cents; AC-001-02 ≤3 products, pick = cheapest within ceiling; AC-001-03 quote cents + options; AC-001-04 checkout returns `approvalUrl`, sends `enrollmentId` + HTTPS `returnUrl`; AC-001-05 status returns `finalAmountCents` from Reap, not quote total — RED then GREEN against T008
- [x] T013 [US1] Live Reap smoke by curl with real key (record in research.md R5): `products/search` SG/SGD "Anker Nano USB-C Hub"; `products/details`; confirm `Reap-Version`; capture real amount shape; adjust `to_cents`/`_product_out` if needed. **Stop and show request/response if a call fails twice.**
- [x] T014 [US1] `scripts/happy_path.sh` (AC-001-06 [e2e]): `PUBLIC_URL` required; intent → search → quote → checkout → poll until terminal; prints `orderId`, `finalAmountCents`; non-zero exit on any failure; uses `jq`
- [ ] T015 [US1] After enrollment ACTIVE (human): run T014 end to end; fix anything Reap returns differently; commit "happy path passes"

**Checkpoint**: `scripts/happy_path.sh` exits 0 with an order reference.

## Phase 4: US2 — Limit blocks over-budget (P2)

- [x] T016 [P] [US2] `test_api.py`: AC-001-08 checkout over limit → 403 with `overByCents`, Reap checkout NOT called; AC-001-10 `PUT /api/limit` then quote re-evaluates with new limit
- [x] T017 [US2] `mobile/App.tsx` Quote screen: pay button disabled when `!limit.allowed`; alert shows `overByCents`; "Change limit" ghost button (AC-001-09 manual check noted)
- [x] T018 [US2] Quickstart §5 run live: lower limit to 1000¢, confirm 403; restore 15000¢

## Phase 5: US3 — Re-pricing, decline, home (P3)

- [x] T019 [P] [US3] `test_api.py`: AC-001-11 shipping-option change re-prices + re-evaluates; AC-001-13 home fields incl. `vaultSource`, `cardLast4`; AC-001-15 Reap 4xx → 502 with verbatim request/response, exactly one Reap call (no retry)
- [x] T020 [US3] `main.py` `/api/home`: `cardLast4` from enrollment `paymentMethod.last4` when ACTIVE (cache), else `CARD_LAST4` env, never a fake default
- [x] T021 [US3] `mobile/App.tsx`: Home vault card shows "Mock balance (Kwal vault pending)" when `vaultSource !== 'kwal'`; empty-orders copy (AC-001-14); Paid shows delivery option; decline/cancel toast "Nothing was charged" (AC-001-12 manual check)
- [ ] T022 [US3] Observe in sandbox and record in research.md: expired quote at checkout; abandoned approval terminal state. Remove the two `[NEEDS CLARIFICATION]` markers from spec.md with the observed behaviour (constitution VIII)

## Phase 6: Polish, converge, G3

- [ ] T023 Phone run via Expo Go against `PUBLIC_URL`; fix layout/copy against `design/glance-app-mockup.html`
- [x] T024 `README.md`: what it is, run steps, env table, demo flow, link to film; no secrets
- [x] T025 Traceability table in `specs/001-agent-purchase/traceability.md`: each AC → test name or "manual check: …"
- [ ] T026 `/speckit-converge`; then request G3 with `happy_path.sh` output + phone video

## Dependencies

Setup → Foundational (T004–T011) → US1 (T012–T015) → US2 (T016–T018) → US3 (T019–T022) → Polish.
T013 needs the real key only (have it). T015/T018/T022 need `PUBLIC_URL` + ACTIVE enrollment (human, in progress).
[P] tasks touch different files and can be done together.
