# Scope lock: overrides anything larger in context.md and sdd-runsheet.md

Code freeze is 8:00 pm SGT today. Build ONE happy path only.

## In scope
- Backend (Python, FastAPI, deployed on HTTPS, state in memory):
  POST /api/intent, /api/search, /api/quote, /api/checkout,
  GET /api/checkout/:id, GET /api/home, PUT /api/limit, GET /done
- Frontend: a React Native mobile app (Expo) that implements the screens,
  copy and styles of design/glance-app-mockup.html. Talks only to the
  backend. The mockup HTML is the visual reference, not shipped code.
- Approval: open Reap's nextAction.url in an in-app browser/WebView;
  /done returns the user to the Paid screen.
- Limit check as a pure function with unit tests. Money in whole cents.
- One script, scripts/happy_path.sh, that runs search -> quote -> checkout ->
  status with curl and prints the order reference.

## Out of scope: do not build
Database, auth and accounts, variant selection (use defaultVariant), order
history beyond the current session, recurring purchases, Kwal integration
(a human handles it; show the vault balance from env var VAULT_BALANCE until
told otherwise), CI, traceability tooling, extra screens, refactors.

## Process
- One spec: "Agent purchase, end to end". Run specify -> clarify -> plan ->
  tasks -> implement. I approve G1 and G2 with one line each. Spend at most
  20 minutes before implementing.
- G3 = scripts/happy_path.sh passes and one purchase completes in the app
  on a phone.
- Commit after every working slice. Report after each slice in three
  lines: what works, what does not, what is next.
- If a Reap call fails twice, stop and show me the request and response.
- If a task will take more than 20 minutes, tell me before starting it.

## Timeline (SGT)
| Time | Work | Checkpoint |
|---|---|---|
| 4:50-5:15 | Repo, Spec Kit, constitution, backend deployed, card enrolled | Enrollment is ACTIVE |
| 5:15-5:35 | Specify, clarify, plan, approve | Stop refining at 5:35 |
| 5:35-6:30 | Backend: search, quote, limit check, checkout, status | Happy path passes by curl |
| 6:30-7:30 | Build the React Native screens against the backend | One purchase works on a phone |
| 7:30-8:00 | Run it on a phone, fix, freeze | Code freeze at 8:00 |
| 8:00-8:45 | Record the demo, add the film, README, submit | Submitted by 8:45 |

## Fallbacks
- 5:45, search returns nothing for the item: switch to any product the
  sandbox does return.
- 6:30, hosted approval is flaky: rely on the X-Simulate-Checkout: COMPLETED
  header and show the approval step from the mockup.
- 6:30, Kwal vault not ready: go Reap-only, label the vault balance as
  sample, pitch the "Most Worthwhile Problem" track.
- 7:15, app not wired: stop, and record the mockup alongside the backend
  calls running for real.
