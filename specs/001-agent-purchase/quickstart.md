# Quickstart: validate Agent Purchase end to end

## Prerequisites
- `backend/.env` with `REAP_API_KEY`, `REAP_VERSION`, `PUBLIC_URL` (HTTPS), `SHOP_COUNTRY=SG`, `SHOP_CURRENCY=SGD`, Singapore `SHIP_*`, `BUYER_EMAIL`. After enrollment: `REAP_ENROLLMENT_ID`.
- Python 3.10+, Poetry; Node 20+; Expo Go on the phone; `cloudflared`.

## 1. Unit + API tests (fast, no network)
```bash
cd backend && poetry install && poetry run pytest -q
```
Expect: all green; names contain `AC-001-07`, `AC-001-08`, `AC-001-10`, `AC-001-11`, `AC-001-13`, `AC-001-15`, etc.

## 2. Run the backend on HTTPS
```bash
cd backend && poetry run fastapi dev app/main.py --port 8000
cloudflared tunnel --url http://localhost:8000      # copy https URL -> PUBLIC_URL, restart backend
curl -s $PUBLIC_URL/health                           # {ok:true, reapKey:true, ...}
```

## 3. Enroll the test card (once, human)
```bash
curl -s -X POST $PUBLIC_URL/api/enroll -H 'content-type: application/json' -d '{}' | jq .nextAction.url
# open the URL on the phone, enter the card (x -> 4), OTP 456789 if asked
curl -s $PUBLIC_URL/api/enrollment | jq .status     # poll until ACTIVE, then set REAP_ENROLLMENT_ID
```

## 4. Happy path by curl (AC-001-06 [e2e], G3 evidence)
```bash
PUBLIC_URL=$PUBLIC_URL scripts/happy_path.sh
```
Expect: prints query → ≤3 products → quote with `totalCents` and `limit.allowed=true` → `checkoutId` + `approvalUrl` → polls to `COMPLETED` → prints `orderId` and `finalAmountCents`. Exit 0.

## 5. Over-limit block (AC-001-08)
```bash
curl -s -X PUT $PUBLIC_URL/api/limit -H 'content-type: application/json' -d '{"perPurchaseCents":1000}'
# re-run step 4 up to checkout: expect HTTP 403 with overByCents and no checkout created
curl -s -X PUT $PUBLIC_URL/api/limit -H 'content-type: application/json' -d '{"perPurchaseCents":15000}'
```

## 6. Phone demo (manual checks AC-001-09, 12, 14)
```bash
cd mobile && npm install && npx tsc --noEmit
EXPO_PUBLIC_API_URL=$PUBLIC_URL npx expo start      # scan QR with Expo Go
```
Walk: Home (mock balance labelled, limit S$150, empty-state copy) → Ask → Results (pick preselected) → Quote (meter) → Review and pay → Reap page in WebView → Paid (orderId, final amount, delivery) → Home shows the order. Then: lower the limit below the quote and confirm the pay button is disabled with the over amount shown; cancel on the hosted page and confirm the "nothing was charged" toast.

## 7. Observations to record in research.md
- Expired quote at checkout: status code + body.
- Abandoned approval (no simulate header): does `GET /agentic/checkouts/:id` reach a terminal state, and when?
